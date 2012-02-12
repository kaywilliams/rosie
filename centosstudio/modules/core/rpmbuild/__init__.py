#
# Copyright (c) 2011
# CentOS Solutions, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import optparse
import os
import re
import signal 
import subprocess
import yum

from centosstudio.util import magic
from centosstudio.util import pps 
from centosstudio.util import shlib 

from centosstudio.util.rxml        import datfile
from centosstudio.util.rxml.errors import XmlPathError

from centosstudio.callback     import TimerCallback
from centosstudio.cslogging    import L1, MSG_MAXWIDTH
from centosstudio.errors       import (CentOSStudioError, 
                                       CentOSStudioEventError)
from centosstudio.main         import Build
from centosstudio.validate     import (DefinitionValidator,
                                       InvalidConfigError)

from centosstudio.event import Event, CLASS_META

from centosstudio.modules.shared import PickleMixin
from centosstudio.modules.shared import ExecuteMixin

YUMCONF = '''
[main]
cachedir=
logfile=/depsolve.log
gpgcheck=0
reposdir=/
reposdir=/
exclude=*debuginfo*

[srpm_repo]
name = Source RPM Repo
baseurl = %s
'''

# -------- Metaclass for creating RPM Events -------- #
class RPMEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)


# -------- Methods for RPM Events -------- #
def __init__(self, ptr, *args, **kwargs):
  Event.__init__(self,
    id = self.rpmid + "-rpm", # self.rpmid provided during class creation
    parentid = 'rpmbuild',
    ptr = ptr,
    version = 1.01,
    requires = ['rpmbuild-data', 'build-machine'],
    provides = ['repos', 'source-repos', 'comps-object'],
    config_base = '/*/rpmbuild/rpm[@id=\'%s\']' % self.rpmid,
  )

  self.DATA = {
    'input':     [],
    'config':    ['.'],
    'variables': [],
    'output':    [],
  }

  self.srpm_dir = self.mddir / 'srpm'
  self.srpm_dir.mkdirs()

  self.macros = {'%{rpmid}': self.rpmid,
                 '%{srpm-dir}': self.srpm_dir,
                }


def setup(self):
  self.diff.setup(self.DATA)
  ExecuteMixin.setup(self)

  # add srpm if path provided (add_xpath ignores request if xpath missing)
  self.io.add_xpath('srpm-path', self.srpm_dir)

  # find srpm in srpm repository if repository provided
  url = pps.path(self.config.get('srpm-repo/text()', ''))
  if url:
    yumconf = self.mddir / 'yum/yum.conf'
    yumconf.dirname.mkdirs()
    yumconf.write_text(YUMCONF % url)

    try:
      yb = yum.YumBase()
      yb.preconf.fn = fn=str(yumconf)
      yb.preconf.root = str(self.mddir / 'yum')
      yb.preconf.init_plugins = False
      yb.doRpmDBSetup()
      yb.conf.cache = 0
      yb.doRepoSetup()
      yb.doSackSetup(archlist=['src'])
      pl = yb.doPackageLists(patterns=[self.rpmid])
    except yum.Errors.RepoError, e:
      raise InvalidRepoError(url=url)

    if pl.available:
      self.io.add_fpath( url / '%s.rpm' % str(pl.available[0]), self.srpm_dir )
    else:
      raise SrpmNotFoundError(name=self.rpmid, url=url)

  # execute user-provided script to create and copy srpm to a dir we specify
  if self.config.get('srpm-script/text()', ''):
    script = self.mddir / 'srpm_script'
    script.write_text(self.config.get('srpm-script/text()'))
    script.chmod(0750)

    self._execute_local(script)
    




def run(self):
  self.io.process_files(cache=True)
  
# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['RpmBuildEvent', 'BuildMachineEvent',],
    description = 'modules that create system-specific RPMs',
  )

  # create event classes based on user configuration
  for config in ptr.definition.xpath('/*/rpmbuild/rpm', []):

    # convert user provided id to a valid class name
    id = config.get('@id')
    name = re.sub('[^0-9a-zA-Z_]', '', id)
    name = '%sRpmEvent' % name.capitalize()

    # create new class
    exec """%s = RPMEvent('%s', 
                          (ExecuteMixin, Event), 
                          { 'rpmid'   : '%s',
                            '__init__': __init__,
                            'setup'   : setup,
                            'run'     : run,
                          }
                         )""" % (name, name, id) in globals()

    # update module info with new classname
    module_info['events'].append(name)

  return module_info

# -------- Events -------- #
class RpmBuildEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'rpmbuild',
      parentid = 'os-events',
      ptr = ptr,
      properties = CLASS_META,
      version = '1.00',
      requires = ['publish-setup-options'],
      provides = ['rpmbuild-data','gpg-signing-keys', 'os-content',],
      suppress_run_message = False 
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'variables': [],
      'output':    []
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.cvars['rpmbuild-data'] = {}

    self.pubkey = self.mddir/'RPM-GPG-KEY-%s' % self.solutionid
    self.seckey = self.mddir/'RPM-GPG-KEY-%s-secret' % self.solutionid
    if self.config.get('gpgsign/passphrase/text()', None) is None:
      self.passphrase=''
    else:
      self.passphrase = str(self.config.get('gpgsign/passphrase/text()'))

    self.DATA['variables'].extend(['pubkey', 'seckey', 'passphrase'])

  def run(self):
    self.get_signing_keys()
    self.DATA['output'].extend([self.pubkey, self.seckey])

  def apply(self):
    self.cvars['gpg-signing-keys'] = { 'pubkey': self.pubkey,
                                       'seckey': self.seckey,
                                       'passphrase': self.passphrase }

  def verify_pubkey_exists(self):
    "pubkey exist"
    self.verifier.failUnlessExists(self.pubkey)

  def verify_seckey_exists(self):
    "seckey exist"
    self.verifier.failUnlessExists(self.seckey)

  #------- Helper Methods -------#

  def get_signing_keys(self):
    if not hasattr(self, 'datfile'): 
      self.datfile = datfile.parse(self._config.file)

    if self.config.get('gpgsign', None) is None:
      self.get_keys_from_datfile() or self.create_keys()
    else:
      self.get_keys_from_config() 

  def get_keys_from_config(self):
    pubtext = self.config.get('gpgsign/public/text()', '')
    sectext = self.config.get('gpgsign/secret/text()', '')
    self.write_keys(pubtext, sectext)
    self.validate_keys(map = { self.pubkey: 'public', self.seckey: 'secret' })


    # remove generated keys from datfile, if exist
    for key in ['pubkey', 'seckey']:
      elem = self.datfile.get('/*/rpms/%s/%s' % (self.id, key), None)
      if elem is not None:
        elem.getparent().remove(elem)

    self.datfile.write()

  def get_keys_from_datfile(self):
    try:
      pubtext = self.datfile.get('/*/rpms/%s/pubkey/text()' % self.id,)
      sectext = self.datfile.get('/*/rpms/%s/seckey/text()' % self.id,)
    except XmlPathError:
      return False # no keys in datfile
   
    self.write_keys(pubtext, sectext)

    return True # keys in datfile

  def create_keys(self):
    homedir = self.mddir/'homedir'
    pubring = homedir/'pubring.gpg'
    secring = homedir/'secring.gpg'

    homedir.rm(recursive=True, force=True)
    homedir.mkdir()
    homedir.chmod(0700)

    name = "%s signing key" % self.solutionid

    cmd = """gpg --quiet --batch --gen-key <<EOF
     Key-Type: DSA
     Key-Length: 1024
     Subkey-Type: ELG-E
     Subkey-Length: 1024
     Name-Real: %s
     Expire-Date: 0
     %%pubring %s
     %%secring %s
EOF""" % (name, pubring, secring)

    rngd = pps.path('/sbin/rngd')

    self.logger.log(2, L1('generating GPG Signing Key'))
    if rngd.exists():
      # use rngd to speed gpgkey generation, slightly less secure, but
      # sufficient for RPM-GPG-KEY scenarios.
      p = subprocess.Popen([rngd, '-f', '-r', '/dev/urandom'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
      shlib.execute(cmd)
    finally:
      if rngd.exists(): os.kill(p.pid, signal.SIGTERM)

    shlib.execute('gpg --export -a --homedir %s "%s" > %s' % (homedir, name,
                   self.pubkey))
    shlib.execute('gpg --export-secret-key -a --homedir %s "%s" > %s' % (
                   homedir, name, self.seckey))

    # write to datfile
    root = self.datfile
    uElement = datfile.uElement

    rpms     = uElement('rpms', parent=root)
    parent   = uElement(self.id, parent=rpms)
    pubkey   = uElement('pubkey', parent=parent, text=self.pubkey.read_text())
    seckey   = uElement('seckey', parent=parent, text=self.seckey.read_text())

    root.write()

  def write_keys(self, pubtext, sectext):
    if not self.pubkey.exists() or not pubtext == self.pubkey.read_text():
      self.pubkey.write_text(pubtext)
    if not self.seckey.exists() or not sectext == self.seckey.read_text():
      self.seckey.write_text(sectext)

  def validate_keys(self, map):
    for key in map:
      if not magic.match(key) == eval(
        'magic.FILE_TYPE_GPG%sKEY' % map[key][:3].upper()):
        raise InvalidKeyError(map[key])


class BuildMachineEvent(PickleMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build-machine',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = '1.00',
      requires = ['base-treeinfo', ],
      provides = ['build-machine'],
      conditional = True,
    )

    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'variables': [], 
      'config':    [],
      'input':     [],
    }

    PickleMixin.__init__(self)

  def validate(self):
    try:
      import libvirt
    except ImportError:
      raise CentOSStudioError(
        "[%s] System Configuration Error: The definition file at '%s' specifies RPMs to build. However, this machine is not configured for general-purpose RPM building. See the CentOS Studio User Manual for information on system requirements for building RPMs, which include hardware and software support for building and hosting virtual machines."
        % (self.moduleid, self._config.file))

    if not self.config.get('definition/text()', ''):
      raise InvalidConfigError(self._config.file,
      "\n[%s]: a 'definition' element is required for building rpms" 
      % self.id)

  def setup(self):
    self.diff.setup(self.DATA)

    self.definition = self.config.get('definition/text()', '')
    self.io.validate_input_file(self.definition)
    self.DATA['input'].append(self.definition)

  def run(self):
    # start timer
    msg = "creating/updating build machine"
    if self.logger:
      timer = TimerCallback(self.logger)
      timer.start(msg)
    else:
      timer = None

    # initialize builder
    try:
      builder = Build(self._get_options(), [self.definition])
    except CentOSStudioError, e:
      raise BuildMachineCreationError(definition=self.definition, 
                                      error=e,
                                      idstr='',
                                      sep = MSG_MAXWIDTH * '=',)

    # build machine
    try:
      builder.main()
    except CentOSStudioError, e:
      raise BuildMachineCreationError(definition=self.definition, 
                                      error=e,
                                      idstr="--> build machine id: %s\n" %
                                            builder.solutionid,
                                      sep = MSG_MAXWIDTH * '=')

    # stop timer
    if timer: timer.end()

    # cache hostname
    self.pickle({'hostname': builder.cvars['publish-setup-options']['hostname']})

  def apply(self):
    self.cvars['build-machine'] = self.unpickle().get('hostname', None)


  def _get_options(self):
    parser = optparse.OptionParser()
    parser.set_defaults(**dict(
      logthresh = 0,
      logfile   = self.options.logfile,
      libpath   = self.options.libpath,
      sharepath = self.options.sharepath,
      force_modules = [],
      skip_modules  = [],
      force_events  = [],
      skip_events   = [],
      mainconfigpath = self.options.mainconfigpath,
      enabled_modules  = [],
      disabled_modules = [],
      list_modules = False,
      list_events = False,
      no_validate = False,
      validate_only = False,
      clear_cache = False,
      debug = self.options.debug,))

    opts, _ = parser.parse_args([])
    
    return opts


# -------- Error Classes --------#
class InvalidRepoError(CentOSStudioEventError):
  message = ("Cannot retrieve repository metadata (repomd.xml) for repository "
             "'%(url)s'. Please verify its path and try again.\n")

class SrpmNotFoundError(CentOSStudioEventError):
  message = "No srpm '%(name)s' found at '%(url)s'\n" 

class BuildMachineCreationError(CentOSStudioEventError):
  message = "Error creating or updating RPM build machine.\n%(sep)s\n%(idstr)s--> build machine definition: %(definition)s\n--> error:%(error)s\n"

class InvalidKeyError(CentOSStudioEventError):
  message = "The %(type)s key provided does not appear to be valid."
