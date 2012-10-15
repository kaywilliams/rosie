
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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
from ConfigParser import ConfigParser
from UserDict import DictMixin

import copy 
import lxml
import pexpect 
import re
import rpmUtils

from systemstudio.util import mkrpm
from systemstudio.util import pps

from systemstudio.errors    import SystemStudioEventError
from systemstudio.event     import Event
from systemstudio.cslogging import L1

from systemstudio.util.rxml import datfile

from systemstudio.modules.shared import ShelveMixin

__all__ = ['RpmBuildMixin', 'MkrpmRpmBuildMixin', 'Trigger', 
           'TriggerContainer',] 

class RpmBuildMixin(ShelveMixin, mkrpm.rpmsign.GpgMixin):
  """
  Mixin for working with SystemStudio-created rpms including both from-srpm
  (srpmbuild) and mkrpm (config-rpm and release-rpm) rpms
  """
  rpmbuild_mixin_version = "1.02"

  def __init__(self):
    self.conditionally_requires.add('gpg-signing-keys')
    self.provides.add('rpmbuild-data')
    self.rpms = [] # list of rpmbuild dicts (get_rpmbuild_data()) to be 
                   # managed by the mixin
    self.dist = '.el%s' % self.version
    ShelveMixin.__init__(self)

  @property
  def rpm_paths(self):
    return [ x['rpm-path'] for x in self.rpms ]

  def setup(self):
    self.DATA.setdefault('variables', []).append('rpmbuild_mixin_version')
    self._setup_signing_keys()

  def run(self):
    self._sign_rpms()
    self._cache_rpmdata()

    self.DATA['output'].extend(self.rpm_paths)

  def apply(self):
    rpmbuild_data = self.unshelve('rpmbuild_data', '')
    for key in rpmbuild_data:
      self.cvars['rpmbuild-data'][key] = rpmbuild_data[key]

  def verify_rpms_exist(self):
    for rpm_path in self.rpm_paths:
      self.verifier.failUnlessExists(rpm_path)

  def _get_rpmbuild_data(self, rpmpath, 
                         packagereq_type='mandatory', 
                         packagereq_default=None, 
                         packagereq_requires=None):
 
      data = {}
      data['rpm-path']  = pps.path(rpmpath)
  
      # set packagereq attrs used in comps file
      data['packagereq-default']  = packagereq_default
      data['packagereq-requires'] = packagereq_requires
      data['packagereq-type']     = packagereq_type
  
      # set convenience variables for nvra
      info = rpmUtils.miscutils.splitFilename(rpmpath.basename)
  
      data['rpm-name']      = info[0] 
      data['rpm-version']   = info[1]
      data['rpm-release']   = info[2]
      data['rpm-arch']      = info[4]
  
      # get obsoletes - rpmbuild-repo uses these to remove pkgs from comps
      ts = rpmUtils.transaction.initReadOnlyTransaction()
      hdr = rpmUtils.miscutils.hdrFromPackage(ts, rpmpath)
      obsoletes = [ x.DNEVR()[2:] for x in hdr.dsFromHeader('obsoletename') ]
      del ts
      del hdr
  
      data['rpm-obsoletes'] = obsoletes
  
      return data

  def _setup_signing_keys(self):
    if 'gpg-signing-keys' in self.cvars:
      self.gpgsign = self.cvars['gpg-signing-keys'] # convenience variable
      self.pubtext = self.gpgsign['pubkey'].read_text().rstrip()
      self.sectext = self.gpgsign['seckey'].read_text().rstrip()
      self.DATA['variables'].extend(['pubtext', 'sectext', 
                                     'gpgsign[\'passphrase\']'])

  def _sign_rpms(self):
    if self.rpms and 'gpg-signing-keys' in self.cvars:
      self.log(4, L1("signing rpm(s)"))

      # set up homedir - used for signing
      homedir = self.mddir / 'gnupg'
      homedir.rm(recursive=True, force=True)
      homedir.mkdirs()
      homedir.chmod(0700)

      for key in [self.gpgsign['pubkey'], self.gpgsign['seckey']]:
        self.import_key(homedir, key)

      for rpm_path in self.rpm_paths:
        # sign rpm
        self.log(4, L1("%s" % rpm_path.basename))
        command = ('/bin/rpm --resign %s ' 
                   '--define="_signature gpg" '
                   '--define="_gpg_path %s" '
                   '--define="_gpg_name %s" '
                   '--define="_gpgbin /usr/bin/gpg"'
                   % (rpm_path, homedir, self.get_gpgname(homedir)))

        try:
          child = pexpect.spawn(command)
          child.expect('Enter pass phrase:')
          child.sendline(self.gpgsign['passphrase'])
          child.expect(pexpect.EOF)

        except Exception, e:
          message = ("Unable to sign rpm '%s'. The error message was '%s'"
                      % (rpm_path, str(e)))
          raise RpmBuildError(message=message)

        child.close()

        if child.exitstatus != 0:
          message = ("Unable to sign rpm '%s'. The error message was '%s'"
                     % (rpm_path, child.before))
          raise RpmBuildError(message=message)

  def _cache_rpmdata(self):
    if self.rpms:
      rpmbuild_data = {}
      for item in self.rpms:
         rpmbuild_data[item['rpm-name']] = item
    self.shelve('rpmbuild_data', rpmbuild_data)


class MkrpmRpmBuildMixin(RpmBuildMixin):
  """
  Mixin for creating rpms from scratch using util.mkrpm
  """
  mkrpmbuild_mixin_version = "1.01"

  def __init__(self, *args, **kwargs):
    RpmBuildMixin.__init__(self)

  def setup(self, name=None, version=None, arch=None, desc=None, 
            summary=None, license=None, author=None, email=None, 
            requires=[], provides=[], obsoletes=[], force_release=None, 
            rpmconf=None):

    # container for info that should be tracked in variables
    # release should not go here since it is incremented in run
    self.rpminfo = dict(
      name = name,
      version = version or self.version,
      arch = arch or 'noarch',
      desc = desc,
      summary = summary,
      author  = author,
      email = email,
      license = license or 'GPLv2',
      requires = requires,
      provides = provides,
      obsoletes = obsoletes,
      )

    rpmconf = rpmconf or self.config
    self.rpminfo['obsoletes'].extend(rpmconf.xpath('obsoletes/text()', []))
    self.rpminfo['provides'].extend([ x for x in self.rpminfo['obsoletes']])
    self.rpminfo['requires'].extend(rpmconf.xpath('provides/text()', []))
    self.rpminfo['requires'].extend(rpmconf.xpath('requires/text()', []))

    self.force_release = force_release
    self.build_folder  = self.mddir / 'build'
    self.source_folder = self.build_folder / 'source'

    self.diff.setup(self.DATA)
    self.DATA.setdefault('variables', []).extend(['mkrpmbuild_mixin_version', 
                                                  'rpminfo', 'force_release'])

    RpmBuildMixin.setup(self) # deals with gpg signing

  def run(self):
    release = self._get_release()

    # create build object
    self.rpm = RpmBuildObject(self, release+self.dist, 
                              copy.deepcopy(self.rpminfo))
    R = self.rpm

    for path in [ self.build_folder, R.rpm_path, R.srpm_path ]:
      path.rm(recursive=True, force=True)
    self.build_folder.mkdirs()
    self.generate()
    R.write_spec()
    R.write_manifest()

    self.log(1, L1("building %s-%s-%s.%s.rpm" % \
                   (R.name, R.version, R.release, R.arch)))

    try:
      mkrpm.build(R.build_folder, self.mddir, createrepo=False,
                  bdist_base=R.bdist_base, rpm_base=R.rpm_base,
                  dist_dir=R.dist_dir, keep_source=True,
                  quiet=(int(self.logger.threshold) < 5))
    except mkrpm.rpmbuild.RpmBuilderException, e:
      raise RpmBuildFailedException(message=str(e))

    self._save_release(release)
    self.DATA['output'].append(self.rpm.build_folder)

    self.rpms = [ self._get_rpmbuild_data(R.rpm_path) ]
    RpmBuildMixin.run(self)

  def apply(self):
    RpmBuildMixin.apply(self)

  def _get_release(self):
    if self.force_release: # use provided release
      return str(self.force_release)

    else: # bump calculated release  
      self.datfile = self.parse_datfile()
      release = self.datfile.getxpath('/*/%s/release/text()' %
                                (self.id), '0')
      return str(int(release)+1)

  def _save_release(self, release):
    root = self.parse_datfile()
    uElement = datfile.uElement
    parent   = uElement(self.id, parent=root)
    child    = uElement('release', parent=parent, text=release)
    root.write()

  #----------- OPTIONAL METHODS --------#
  def generate(self):
    pass

  # determine what files are ghost
  def get_ghost_files(self): return None

  # rpm scripts
  def get_build(self):        return None
  def get_clean(self):        return None
  def get_install(self):      return None
  def get_post(self):         return None
  def get_postun(self):       return None
  def get_pre(self):          return None
  def get_prep(self):         return None
  def get_preun(self):        return None
  def get_verifyscript(self): return None

  # trigger scripts
  def get_triggers(self):     return None


class RpmBuildObject:
  def __init__(self, ptr, release, rpminfo):
    self.ptr     = ptr
    self.release = release 
    self.name    = rpminfo['name']
    self.version = rpminfo['version']
    self.arch    = rpminfo['arch']
    self.desc    = rpminfo['desc']
    self.summary = rpminfo['summary']
    self.license = rpminfo['license']
    self.author  = rpminfo['author']

    self.obsoletes = rpminfo['obsoletes']
    self.requires  = rpminfo['requires']
    self.provides  = rpminfo['provides']

    # RPM build variables
    self.build_folder  = ptr.build_folder
    self.source_folder = ptr.source_folder 
    self.bdist_base    = self.build_folder / 'rpm-base'
    self.rpm_base      = self.build_folder / 'rpm'
    self.dist_dir      = self.build_folder / 'dist'

  #------------- PROPERTIES --------------#
  @property
  def rpm_path(self):
    return self.ptr.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
             (self.name, self.version, self.release, self.arch)

  @property
  def srpm_path(self):
    return self.ptr.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
           (self.name, self.version, self.release)

  @property
  def data_files(self):
    data_files = {}
    for item in self.source_folder.findpaths(type=pps.constants.TYPE_DIR,
                                             mindepth=1):
      files = item.findpaths(type=pps.constants.TYPE_NOT_DIR,
                             mindepth=1, maxdepth=1)
      if files:
        data_files.setdefault('/' / item.relpathfrom(self.source_folder), []).extend(files)
    return data_files

  #--------- RPM BUILD HELPER METHODS ---------#


  def write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'

    spec = ConfigParser()

    # metadata section
    M = 'metadata'
    spec.add_section(M)

    spec.set(M, 'name',             self.name)
    spec.set(M, 'long_description', self.desc)
    spec.set(M, 'description',      self.summary)
    spec.set(M, 'author',           self.author)
    spec.set(M, 'version',          self.version)

    if self.license: spec.set(M, 'license', self.license)

    # bdist_rpm section
    B = 'bdist_rpm'
    spec.add_section(B)

    spec.set(B, 'force_arch',        self.arch)
    spec.set(B, 'distribution_name', self.name)
    spec.set(B, 'release',           self.release)

    if self.provides:  spec.set(B, 'provides',  ' '.join(self.provides))
    if self.requires:  spec.set(B, 'requires',  ' '.join(self.requires))
    if self.obsoletes: spec.set(B, 'obsoletes', ' '.join(self.obsoletes))

    # get the various script types
    build   = self.ptr.get_build()
    clean   = self.ptr.get_clean()
    install = self.ptr.get_install()
    post    = self.ptr.get_post()
    postun  = self.ptr.get_postun()
    pre     = self.ptr.get_pre()
    prep    = self.ptr.get_prep()
    preun   = self.ptr.get_preun()
    verify  = self.ptr.get_verifyscript()

    triggers = self.ptr.get_triggers()

    ghost = self.ptr.get_ghost_files()

    # add to bdist_rpm
    if build:   spec.set(B, 'build_script',   build)
    if clean:   spec.set(B, 'clean_script',   clean)
    if install: spec.set(B, 'install_script', install)
    if post:    spec.set(B, 'post_install',   post)
    if postun:  spec.set(B, 'post_uninstall', postun)
    if pre:     spec.set(B, 'pre_install',    pre)
    if prep:    spec.set(B, 'prep_script',    prep)
    if preun:   spec.set(B, 'pre_uninstall',  preun)
    if verify:  spec.set(B, 'verify_script',  verify)

    if triggers:
      trigcfg = self.build_folder / 'triggers.cfg'
      triggers.write_config(trigcfg)
      spec.set(B, 'trigger_configs', trigcfg)

    if ghost: spec.set(B, 'ghost_files', '\n\t'.join(ghost))

    # distribution related data
    D = 'distribution'
    spec.add_section(D)

    self.add_data_files(spec, D)
    #self.add_config_files(spec, B) #config-rpm manages independently
    self.add_doc_files(spec, B)

    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def write_manifest(self):
    manifest = ['setup.py', 'setup.cfg']
    manifest.extend( [ x.relpathfrom(self.build_folder) for x in
                       self.source_folder.findpaths(
                         type=pps.constants.TYPE_NOT_DIR) ])
    (self.build_folder/'MANIFEST').write_lines(manifest)

  def add_data_files(self, spec, section):
    data = []
    for dir, files in self.data_files.items():
      data.append('\t%s : %s' % (dir, ', '.join(files)))
    if data: spec.set(section, 'data_files', '\n'.join(data))

  def add_config_files(self, spec, section):
    cfg = []
    for dir,files in self.data_files.items():
      if dir.startswith('/etc'): # config files
        cfg.extend([ dir/x.basename for x in files ])
    if cfg: spec.set(section, 'config_files', '\n\t'.join(cfg))

  def add_doc_files(self, spec, section):
    doc = []
    if (self.source_folder / 'COPYING').exists():
      doc.append('COPYING')
    for dir,files in self.data_files.items():
      if dir.startswith('/usr/share/doc'):
        doc.extend([ dir/x.basename for x in files ])
    if doc: spec.set(section, 'doc_files', '\n\t'.join(doc))

class TriggerContainer(list):
  def __init__(self, iterable=None):
    iterable = iterable or []
    self.check(iterable)
    list.__init__(self, iterable)

  def write_config(self, file):
    lines = []
    for trigger in self:
      lines.append(str(trigger))
      lines.append('')
    file.write_lines(lines)

  def extend(self, item):
    self.check(item)
    list.extend(self, item)

  def append(self, item):
    self.check(item)
    list.append(self, item)

  def insert(self, index, item):
    self.check(item)
    list.insert(self, index, item)

  def check(self, item):
    if not hasattr(item, '__iter__'):
      item = [item]
    if isinstance(item, Trigger):
      return
    for x in item:
      if not isinstance(x, Trigger):
        raise TypeError("Trying to add non-Trigger object '%s' to TriggerContainer" % x)


class Trigger(dict):
  def __init__(self, id, **kwargs):
    self.id = id
    dict.__init__(self, **kwargs)

  def __str__(self):
    lines = ['[%s]' % self.id]
    if 'triggerid' not in self:
      lines.append('triggerid = %s' % self.id)
    for key, value in self.iteritems():
      if hasattr(value, '__iter__'):
        val = '\n\t'.join(value)
        lines.append('%s = %s' % (key, val.strip('\n')))
      else:
        lines.append('%s = %s' % (key, value))
    return '\n'.join(lines)


class RpmBuildError(SystemStudioEventError):
  message="%(message)s"

class RpmBuildFailedException(RpmBuildError):
  message = "RPM build failed.  See build output below for details:\n%(message)s"


