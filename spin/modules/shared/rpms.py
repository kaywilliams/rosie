#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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

import colorsys
import re

from rendition import mkrpm
from rendition import pps
from rendition import rxml

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event
from spin.logging   import L1

__all__ = ['InputFilesMixin', 'RpmBuildMixin']

VER_X_REGEX = re.compile('[^0-9]*([0-9]+).*')

class InputFilesMixin:
  """
  Mixin that can be used to setup the download and get list of data
  files that are sync'd.
  """
  def __init__(self, install_info):
    self.install_info = install_info
    self.ids = set()

  def _setup_download(self):
    for k,v in self.install_info.items():
      xpath, dst, mode, absolute = v

      if xpath and self.config.pathexists(xpath):
        default_dir = pps.path(dst) / self.config.get(xpath).getparent().get('@dest', '')
        for item in self.config.xpath(xpath, []):
          s,d,f,m = self.io._process_path_xml(item, relpath=default_dir,
                                              absolute=absolute, mode=mode)
          # http paths are absolute and will wipe out this join
          s = self._config.file.dirname / s

          id = self._get_download_id(k)
          self.ids.add(id)

          self.io.add_item(s, self.build_folder//d/f, id=id or s, mode=m)

          self._handle_attributes(id, item)

  def _get_download_id(self, type):
    return type

  def _handle_attributes(self, id, item):
    pass

class RpmBuildMixin:
  def __init__(self, *args, **kwargs):
    self.rpm = RpmBuildObject(self, *args,**kwargs)

  def check(self):
    return self.rpm.release == '0' or \
           not self.rpm.autofile.exists() or \
           self.diff.test_diffs()

  def setup(self):
    self.rpm._setup_build()

  def run(self):
    self.io.clean_eventcache(all=True)

    R = self.rpm

    R.check_release()

    R.build_folder.mkdirs()
    self.generate()
    R.write_spec()
    R.write_manifest()

    self.log(1, L1("building %s-%s-%s.%s.rpm" % \
                   (R.name, R.version, R.release, R.arch)))
    mkrpm.build(R.build_folder, self.mddir, createrepo=False,
                bdist_base=R.bdist_base, rpm_base=R.rpm_base,
                dist_dir=R.dist_dir, keep_source=True,
                quiet=(self.logger.threshold < 5))

    R.save_release()

    self.DATA['output'].append(R.rpm_path)
    self.DATA['output'].append(R.srpm_path)

  def apply(self):
    self.io.clean_eventcache()

    R = self.rpm

    custom_rpm_data = {}

    custom_rpm_data['packagereq-default']  = R.packagereq_default
    custom_rpm_data['packagereq-requires'] = R.packagereq_requires
    custom_rpm_data['packagereq-type']     = R.packagereq_type

    custom_rpm_data['rpm-name']      = R.name
    custom_rpm_data['rpm-obsoletes'] = R.obsoletes
    custom_rpm_data['rpm-provides']  = R.provides
    custom_rpm_data['rpm-requires']  = R.requires

    custom_rpm_data['rpm-path']  = R.rpm_path
    custom_rpm_data['srpm-path'] = R.srpm_path

    self.cvars['custom-rpms-data'][self.id] = custom_rpm_data

  def verify_rpm_exists(self):
    "rpm exists"
    self.verifier.failUnlessExists(self.rpm.rpm_path)

  def verify_srpm_exists(self):
    "srpm exists"
    self.verifier.failUnlessExists(self.rpm.srpm_path)

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
  def __init__(self, ptr, name, desc, summary, license=None,
               provides=None, obsoletes=None, requires=None,
               packagereq_type='mandatory', packagereq_default=None,
               packagereq_requires=None):
    self.ptr = ptr

    self.desc    = desc
    self.name    = name
    self.summary = summary
    self.license = license

    self.obsoletes = obsoletes or []
    self.requires  = requires  or []
    self.provides  = provides  or []

    if self.ptr.config.get('@use-default-set', 'True') not in BOOLEANS_TRUE:
      self.obsoletes = []

    self.packagereq_type     = packagereq_type
    self.packagereq_default  = packagereq_default
    self.packagereq_requires = packagereq_requires

    self.autofile = self.ptr._config.file + '.dat'

    # RPM build variables
    self.build_folder = self.ptr.mddir / 'build'
    self.bdist_base   = self.ptr.mddir / 'rpm-base'
    self.rpm_base     = self.bdist_base / 'rpm'
    self.dist_dir     = self.bdist_base / 'dist'

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
    for item in self.build_folder.findpaths(type=pps.constants.TYPE_DIR, mindepth=1):
      files = item.findpaths(type=pps.constants.TYPE_NOT_DIR,
                             mindepth=1, maxdepth=1)
      if files:
        data_files.setdefault('/'/item.relpathfrom(self.build_folder), []).extend(files)
    return data_files

  #--------- RPM BUILD HELPER METHODS ---------#
  def setup_build(self, **kwargs):
    if self.autofile.exists():
      self.release = rxml.config.read(self.autofile).get(
       '/distro/%s/rpms/%s/release/text()' %
       (self.ptr.distroid, self.ptr.id), '0')
    else:
      self.release = '0'

    self.obsoletes.extend(self.ptr.config.xpath('obsoletes/text()', []))
    self.obsoletes.extend(kwargs.get('obsoletes', []))

    self.provides.extend([ x for x in self.obsoletes ])
    self.requires.extend(self.ptr.config.xpath('provides/text()', []))
    self.provides.extend(kwargs.get('provides', []))

    self.requires.extend(self.ptr.config.xpath('requires/text()', []))
    self.requires.extend(kwargs.get('requires', []))

    self.ptr.diff.setup(self.ptr.DATA)

    self.arch     = kwargs.get('arch',     'noarch')
    self.author   = kwargs.get('author',   'spin')
    self.fullname = kwargs.get('fullname', self.ptr.fullname)
    if kwargs.has_key('version'):
      self.version = kwargs['version']
    else:
      vermatch = VER_X_REGEX.match(self.ptr.version)
      if vermatch:
        # for interop with 3rd party repofiles that use $releasever
        self.version = vermatch.group(1)
      else:
        self.version = self.ptr.version

  def save_release(self):
    if self.autofile.exists():
      root = rxml.config.read(self.autofile).get('/distro')
    else:
      root = rxml.config.Element('distro')

    distroid = rxml.config.uElement(self.ptr.distroid, parent=root)
    rpms     = rxml.config.uElement('rpms', parent=distroid)
    parent   = rxml.config.uElement(self.ptr.id, parent=rpms)
    release  = rxml.config.uElement('release', parent=parent, text=self.release)

    root.write(self.autofile)

    if self.ptr._config.file.exists():
      # set the mode and ownership of distro.conf.dat and distro.conf to
      # be the same.
      st = self.ptr._config.file.stat()
      self.autofile.chown(st.st_uid, st.st_gid)
      self.autofile.chmod(st.st_mode)

  def check_release(self):
    if ( self.release == '0' or
         not self.autofile.exists() or
         not self.ptr.mdfile.exists() or
         self.ptr.diff.input.difference() or
         self.ptr.diff.variables.difference() or
         self.ptr.diff.config.difference() ):
      self.release = str(int(self.release)+1)

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
    spec.set(B, 'distribution_name', self.fullname)
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
      spec.set(B, 'trigger_dir', self.build_folder)
      spec.set(B, 'triggers', ' '.join(triggers.keys()))
      for id, info in triggers.iteritems():
        trigger = info.get('trigger', id)
        trigin  = info.get('triggerin_script', None)
        trigun  = info.get('triggerun_script', None)
        trigpun = info.get('triggerpostun_script', None)
        flags   = info.get('flags', None)

        lines = ['[%s]' % id, 'trigger = %s' % trigger]
        if trigin  : lines.append('triggerin_script = %s' % trigin)
        if trigin  : lines.append('triggerun_script = %s' % trigun)
        if trigpun : lines.append('triggerpostun_script = %s' % trigpun)
        if flags   : lines.append('flags = %s' % flags)

        (self.build_folder / '%s.cfg' % id).write_lines(lines)

    if ghost: spec.set(B, 'ghost_files', '\n\t'.join(ghost))

    # distribution related data
    D = 'distribution'
    spec.add_section(D)

    self.add_data_files(spec, D)
    self.add_config_files(spec, B)
    self.add_doc_files(spec, B)


    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def write_manifest(self):
    manifest = ['setup.py']
    manifest.extend( [ x.relpathfrom(self.build_folder) for x in
                       self.build_folder.findpaths(
                         type=pps.constants.TYPE_NOT_DIR) ])
    (self.build_folder/'MANIFEST').write_lines(manifest)

  def add_data_files(self, spec, section):
    data = []
    for dir, files in self.data_files.items():
      data.append('%s : %s' % (dir, ', '.join(files)))
    if data: spec.set(section, 'data_files', '\n\t'.join(data))

  def add_config_files(self, spec, section):
    cfg = []
    for dir,files in self.data_files.items():
      if dir.startswith('/etc'): # config files
        cfg.extend([ dir/x.basename for x in files ])
    if cfg: spec.set(section, 'config_files', '\n\t'.join(cfg))

  def add_doc_files(self, spec, section):
    doc = []
    if (self.build_folder / 'COPYING').exists():
      doc.append('COPYING')
    for dir,files in self.data_files.items():
      if dir.startswith('/usr/share/doc'):
        doc.extend([ dir/x.basename for x in files ])
    if doc: spec.set(section, 'doc_files', '\n\t'.join(doc))
