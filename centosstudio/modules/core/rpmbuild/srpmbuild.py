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
import lxml
import optparse
import re
import rpm
import rpmUtils
import signal
import yum

from centosstudio.callback     import TimerCallback
from centosstudio.cslogging    import MSG_MAXWIDTH
from centosstudio.errors       import (CentOSStudioError,
                                       CentOSStudioEventError,
                                       SimpleCentOSStudioEventError)
from centosstudio.event        import Event, CLASS_META
from centosstudio.main         import Build
from centosstudio.util         import pps 
from centosstudio.util         import rxml 

from centosstudio.util.pps.constants import TYPE_NOT_DIR


from centosstudio.modules.shared import (ExecuteMixin, PickleMixin, 
                                         SystemVirtConfigError)

from fnmatch import fnmatch

YUMCONF = '''
[main]
cachedir=/
persistdir=/
logfile=/depsolve.log
gpgcheck=0
reposdir=/
exclude=*debuginfo*

[%s]
name = Source RPM Repo
baseurl = %s
'''


class SrpmBuildMixinEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-%s' % (self.moduleid, self.srpmid), 
      parentid = 'rpmbuild',
      ptr = ptr,
      version = 1.02,
      requires = ['rpmbuild-data', ],
      provides = ['repos', 'source-repos', 'comps-object'],
      config_base = '/*/%s/srpm[@id=\'%s\']' % (self.moduleid, self.srpmid),
    )
  
    try:
      exec "import libvirt" in globals()
      exec "from virtinst import CloneManager" in globals()
    except ImportError:
      raise SystemVirtConfigError(file=self._config.file)
  
    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'input':     [],
      'config':    ['.'],
      'variables': [],
      'output':    [],
    }
  
    self.srpmfile = ''
    self.srpmdir  = self.mddir / 'srpm'
    self.datdir   = self.LIB_DIR / '%s' % self.moduleid
    self.datdir.mkdirs()

    if self.version == "5":
      self.build_dir = pps.path('/usr/src/redhat')
    else:
      self.build_dir = pps.path('/root/rpmbuild')

    PickleMixin.__init__(self)
  
  def setup(self):
    self.diff.setup(self.DATA)
    ExecuteMixin.setup(self)
  
    # resolve macros
    srpmlast = self.unpickle().get('srpmlast', '')
    macros = {'%{srpm-id}': self.srpmid,
              '%{srpm-dir}': self.srpmdir,
              '%{srpm-last}': srpmlast,
             }
    self.config.resolve_macros('.', macros)
  
    # get srpm
    repo = pps.path(self.config.get('repo/text()', ''))
    script = self.config.get('script/text()', '')
    if repo: self._get_srpm_from_repo(repo)
    elif script: self._get_srpm_from_script(script)

    # get base build machine definition
    search_dirs = self.SHARE_DIRS
    search_dirs.insert(0, self.mainconfig.file.dirname)
    default = ''
    for d in search_dirs:
      results = d.findpaths(mindepth=1, type=pps.constants.TYPE_NOT_DIR,
                            glob='%s-%s-%s.definition' % 
                            (self.moduleid, self.version, self.userarch))
      if results:
        default = results[0]
        break

    self.definition = self.config.get('definition/text()', 
                      self.config.get('/*/%s/definition/text()' % self.moduleid,
                      default))
    self.io.validate_input_file(self.definition)
    self.DATA['input'].append(self.definition)

  def run(self):
    self.io.process_files(cache=True)
  
    # cache srpm file and info
    if self.srpmfile: # srpm provided by script
      self.DATA['output'].append(self.srpmfile)
    else: # srpm provided by path or repo
      self.srpmfile = self.io.list_output(what='srpm')[0]
    self.pickle({'srpmlast': self.srpmfile.basename})
    # update definition
    definition = self._update_definition()

    # initialize builder
    try:
      builder = SrpmBuild(definition, self._get_build_machine_options(), [])
    except CentOSStudioError, e:
      raise BuildMachineCreationError(
              definition='based on \'%s\'' % self.definition, 
              error=e, idstr='', sep = MSG_MAXWIDTH * '=',)

    # build machine
    timer = TimerCallback(self.logger)
    timer.start("building '%s'" % self.srpmid)
    try:
      builder.main()
    except CentOSStudioError, e:
      raise BuildMachineCreationError(
                    definition='based on \'%s\'' % self.definition, 
                    error=e, idstr="--> build machine id: %s\n" %
                    builder.solutionid, sep = MSG_MAXWIDTH * '=')
    timer.end()

  def _get_srpm_from_repo(self, repo):
    yumdir = self.mddir / 'yum'
    yumdir.mkdirs()
    yumconf = yumdir / 'yum.conf'
    yumconf.write_text(YUMCONF % (self.id, repo))
    yb = yum.YumBase()
    yb.preconf.fn = fn=str(yumconf)
    yb.preconf.root = str(yumdir)
    yb.preconf.init_plugins = False
    yb.preconf.errorlevel = 0
    yb.doRpmDBSetup()
    yb.conf.cache = 0
    yb.doRepoSetup(self.id)
  
    try:
      yb.doSackSetup(archlist=['src'], thisrepo=self.id)
    except yum.Errors.RepoError:
      raise InvalidRepoError(url=repo)
  
    try:
      srpm = (yb.repos.getRepo(self.id).getPackageSack()
              .returnNewestByName(name=self.srpmid)[0])
    except yum.Errors.PackageSackError:
      raise SrpmNotFoundError(name=self.srpmid, path=repo)
      
    self.io.add_fpath(srpm.remote_url, self.srpmdir, id='srpm')
    del yb; yb = None

  def _get_srpm_from_script(self, script):
    # start with a clean srpmdir
    self.srpmdir.rm(recursive=True, force=True) 
    self.srpmdir.mkdirs()
  
    script_file = self.mddir / 'script'
    script_file.write_text(self.config.get('script/text()'))
    script_file.chmod(0750)
  
    self._execute_local(script_file)
  
    results = self.srpmdir.findpaths(glob='%s-*.src.rpm' % self.srpmid, 
                                      maxdepth=1)
  
    if not results:
      message = ("The script provided for the '%s' srpm did not output an "
                 "srpm beginning with '%s' and ending with '.src.rpm' in the "
                 "location specified by the %%{srpmdir} macro. See the "
                 "CentOS Studio documentation for information on using the "
                 "srpm/script element." % (self.srpmid, self.srpmid))
      raise SimpleCentOSStudioEventError(message=message)
    elif len(results) > 1:
      message = "more than one result: %s" % results
      raise SimpleCentOSStudioEventError(message=message)
    else:
      self.srpmfile = results[0]
      self.DATA['input'].append(self.srpmfile)

  def _update_definition(self):
    name, spec, requires = self._get_srpm_info(self.srpmfile)

    root = rxml.config.parse(self.definition).getroot()

    name =    self.id
    version = self.version
    arch =    self.userarch

    # provide meaningful filename since it is also used for the .dat file
    root.file = self.datdir / '%s-%s-%s.definition' % (name, version, arch)

    # add main element
    if root.find('main') is not None: 
      root.remove(root.find('main'))

    main = rxml.config.Element('main')
    rxml.config.Element('name',    text=name, parent=main)
    rxml.config.Element('version', text=version, parent=main)
    rxml.config.Element('arch',    text=arch, parent=main)

    root.append(main)

    # add srpm requires to config-rpm
    if root.find('config-rpm') is None:
        config = rxml.config.Element('config-rpm')
    else:
        config = root.find('config-rpm')

    child = rxml.config.Element('files', parent=config)
    child.set('destdir', self.build_dir / 'originals')
    child.text = self.srpmfile

    for req in requires:
      child = rxml.config.Element('requires', parent=config)
      child.text = req

    if root.find('config') is None:
      root.append(config)

    #resolve macros
    root.resolve_macros('.', {
      '%{srpm}': self.build_dir / 'originals' / self.srpmfile.basename,
      '%{spec}': self.build_dir / 'SPECS' / spec, })

    return root

  def _get_srpm_info(self, srpm):
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    hdr = rpmUtils.miscutils.hdrFromPackage(ts, srpm)
    name = hdr[rpm.RPMTAG_NAME]
    spec = [ f for f in hdr['FILENAMES'] if '.spec' in f ][0]
    requires = [ r.DNEVR()[2:] for r in hdr.dsFromHeader('requirename') ]
    del ts
    del hdr
    return (name, spec, requires) 

  def _get_build_machine_options(self):
    parser = optparse.OptionParser()
    parser.set_defaults(**dict(
      logthresh = 0,
      logfile   = self.options.logfile,
      libpath   = self.options.libpath,
      sharepath = self.options.sharepath,
      force_modules = [],
      skip_modules  = [],
      force_events  = ['deploy'],
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

  def _copy_results(self, hostname, password):
    # the better way to do this, evenutally, is to add sftp support to pps
    # for now, using paramiko directly...

    # activate system
    connection = libvirt.open('qemu:///system')
    vm = connection.lookupByName(hostname)
    if vm.isActive() == 1:
      pass # vm is active, continue...
    elif vm.create() != 0:
      raise RuntimeError("vm inactive, and failed to start: %s" % hostname)

    try:
      # establish ssh connection
      signal.signal(signal.SIGINT, signal.default_int_handler) #enable ctrl+C
      client = sshlib.get_client(username = 'root', hostname = hostname, 
                                 port = 22, password = password, 
                                 callback = SSHConnectCallback(log))
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())

      # copy files
      rpms = set()
      srpms = set()
      for dir in sftp.listdir(str(self.build_dir/'RPMS')):
          for rpm in sftp.listdir(str(self.build_dir/'RPMS'/dir)):
              if (fnmatch(rpm, self.rpm_glob) and not 
                  fnmatch(rpm, self.rpm_nglob)):
                  rpms.add(self.build_dir/'RPMS'/dir/rpm)

      for srpm in sftp.listdir(str(self.build_dir/'SRPMS')):
          if fnmatch(srpm, self.srpm_glob):
              if self.srpm_nglob and fnmatch(srpm, self.srpm_nglob): 
                  continue # filter out unwanted srpms
              else:
                  srpms.add(self.build_dir/'SRPMS'/srpm)

      for rpm in rpms:
          for dir in self.rpms_dirs:
              sftp.get(str(rpm), str(dir/rpm.basename))

      for srpm in srpms:
          sftp.get(str(srpm), str(self.srpms_dir/srpm.basename))

      # shutdown machine
      chan = client._transport.open_session()
      chan.exec_command('poweroff')
      stdin = chan.makefile('wb', -1)
      stdout = chan.makefile('rb', -1)
      stderr = chan.makefile_stderr('rb', -1)
      for f in ['out', 'err']:
        text = eval('std%s.read()' % f).rstrip()
        if text:
          log(text)
      status = chan.recv_exit_status()
      chan.close()
      client.close()
      if status != 0:
        raise RuntimeError("unable to poweroff vm: %s" % hostname)

    finally:
      # close connection
      if 'sftp' in locals(): sftp.close()
      if 'client' in locals(): client.close()

class SrpmBuild(Build):
  def __init__(self, definition, *args, **kwargs):
    self.definition = definition
    Build.__init__(self, *args, **kwargs)

  def _get_definition(self, options, arguments):
    self.definition = self.definition
    self.definitiontree = lxml.etree.ElementTree(self.definition)


# ------ Metaclass for creating SRPM Build Events -------- #
class SrpmBuildEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)

def __init__(self, ptr, *args, **kwargs):
  SrpmBuildMixinEvent.__init__(self, ptr, *args, **kwargs)


# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = [ ],
    description = 'modules that accept SRPMs and build RPMs',
  )

  # create event classes based on user configuration
  for config in ptr.definition.xpath('/*/srpmbuild/srpm', []):

    # convert user provided id to a valid class name
    id = config.get('@id')
    name = re.sub('[^0-9a-zA-Z_]', '', id)
    name = '%sSrpmBuildEvent' % name.capitalize()

    # create new class
    exec """%s = SrpmBuildEvent('%s', 
                          (SrpmBuildMixinEvent, ExecuteMixin, PickleMixin,), 
                          { 'srpmid'   : '%s',
                            '__init__': __init__,
                          }
                         )""" % (name, name, id) in globals()

    # update module info with new classname
    module_info['events'].append(name)

  return module_info


# -------- Error Classes --------#
class InvalidRepoError(CentOSStudioEventError):
  message = ("Cannot retrieve repository metadata (repomd.xml) for repository "
             "'%(url)s'. Please verify its path and try again.\n")

class SrpmNotFoundError(CentOSStudioEventError):
  message = "No srpm '%(name)s' found at '%(path)s'\n"

class BuildMachineCreationError(CentOSStudioEventError):
  message = ("Error creating or updating RPM build machine.\n%(sep)s\n"
             "%(idstr)s--> build machine definition: %(definition)s\n--> "
             "error:\n%(error)s\n")
