from ConfigParser import ConfigParser

import re

from dims import mkrpm
from dims import pps
from dims import sync
from dims import xmllib

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event, EventExit
from dimsbuild.logging   import L1

__all__ = ['InputFilesMixin', 'LocalFilesMixin', 'ColorMixin', 'RpmBuildMixin']

P = pps.Path

VER_X_REGEX = re.compile('[^0-9]*([0-9]+).*')

class InputFilesMixin:
  def __init__(self):
    self.rpm_dir = self.mddir/'rpm-input'

  def _setup_download(self):
    for k,v in self.installinfo.items():
      xpath, dst, defmode = v
      if xpath and self.config.pathexists(xpath):
        default_dir = P(dst) / P(self.config.get(xpath).getparent().get('@dest', ''))
        for item in self.config.xpath(xpath, []):
          s = P(item.get('text()'))
          d = default_dir / P(item.get('@dest', ''))
          m = item.get('@mode', defmode)
          self.io.setup_sync(self.rpm_dir // d, paths=[s], id=k, defmode=m)

  def _get_files(self):
    sources = {}
    for item in self.rpm_dir.findpaths(type=pps.constants.TYPE_DIR, mindepth=1):
      files = item.findpaths(type=pps.constants.TYPE_NOT_DIR,
                             mindepth=1, maxdepth=1)
      if files:
        sources[P(item[len(self.rpm_dir):])] = files
    return sources


class LocalFilesMixin:
  def __init__(self):
    pass

  def _setup_locals(self):
    newlocals = {}
    for k,v in self.fileslocals.items():
      newkey = k % self.cvars['base-vars']
      newlocals[newkey] = v
      if newlocals[newkey].has_key('locations'):
        newlocs = []
        for loc in newlocals[newkey]['locations']:
          newlocs.append(loc % self.cvars['base-vars'])
        newlocals[newkey]['locations'] = newlocs
    self.fileslocals.clear()
    self.fileslocals.update(newlocals)
    del newlocals

  def _get_files(self):
    sources = {}
    for id in self.fileslocals.keys():
      locations = self.fileslocals[id]['locations']
      file = self.build_folder/id
      filename = file.basename
      filedir = file.dirname
      for l in [ P(x) for x in locations ]:
        installname = l.basename
        installdir = l.dirname
        if filename != installname:
          newfile = filedir/installname
          file.link(newfile)
          id = newfile
        sources.setdefault(installdir, []).append(id)
    return sources


class ColorMixin:
  def __init__(self):
    pass

  def setColors(self, be=False, prefix='0x'):
    # compute the background and foreground colors to use
    self.distroname = self.cvars['source-vars']['fullname']
    self.distroversion = self.cvars['source-vars']['version']
    try:
      self.bgcolor, self.textcolor, self.hlcolor = \
                    IMAGE_COLORS[self.distroname][self.distroversion]
    except KeyError:
      self.bgcolor, self.textcolor, self.hlcolor = IMAGE_COLORS['*']['0']

    # if be (big-endian) is True, convert the colors to big-endian
    if be:
      self.bgcolor = self.toBigEndian(self.bgcolor)
      self.textcolor = self.toBigEndian(self.textcolor)
      self.hlcolor = self.toBigEndian(self.hlcolor)

    if prefix != '0x':
      self.bgcolor = self.bgcolor.replace('0x', prefix)
      self.textcolor = self.textcolor.replace('0x', prefix)
      self.hlcolor = self.textcolor.replace('0x', prefix)

  def toBigEndian(self, color):
    if color.startswith('0x'):
      color = color[2:]
    color = '%s%s' % ((6-len(color))*'0', color) # prepend zeroes to color
    return '0x%s%s%s' % (color[4:], color[2:4], color[:2])


class RpmBuildMixin:
  def __init__(self, rpm_name, rpm_desc, rpm_summary,
               default_provides=[], default_obsoletes=[], default_requires=[]):
    self.rpm_desc = rpm_desc
    self.rpm_name = rpm_name
    self.rpm_summary = rpm_summary
    self.default_obsoletes = default_obsoletes
    self.default_provides = default_provides
    self.default_requires = default_requires
    self.autofile = P(self._config.file + '.dat')

    # RPM build variables
    self.bdist_base = self.mddir / 'rpm-base'
    self.rpm_base = self.bdist_base / 'rpm'
    self.dist_dir = self.bdist_base / 'dist'

  def _setup_build(self, **kwargs):
    if self.autofile.exists():
      self.rpm_release = xmllib.tree.read(self.autofile).get(
       '/distro/%s/rpms/%s/release/text()' % (self.pva, self.id), '0')
    else:
      self.rpm_release = '0'

    if self.config.get('@use-default-set', 'True'):
      self.rpm_obsoletes = self.default_obsoletes
    else:
      self.rpm_obsoletes = []
    if self.config.pathexists('obsoletes/text()'):
      self.rpm_obsoletes.extend(self.config.xpath('obsoletes/text()', []))
    if kwargs.has_key('obsoletes'):
      self.rpm_obsoletes.extend(kwargs['obsoletes'])

    self.rpm_provides = [ x for x in self.rpm_obsoletes ]
    if self.default_provides:
      self.rpm_provides.extend(self.default_provides)
    if kwargs.has_key('provides'):
      self.rpm_provides.extend(kwargs['provides'])

    if self.default_requires:
      self.rpm_requires = self.default_requires
    else:
      self.rpm_requires = []
    if self.config.pathexists('requires/text()'):
      self.rpm_requires.extend(self.config.xpath('requires/text()', []))
    if kwargs.has_key('requires'):
      self.rpm_requires.extend(kwargs['requires'])

    self.diff.setup(self.DATA)

    self.rpm_arch = kwargs.get('arch', 'noarch')
    self.rpm_author = kwargs.get('author', 'dimsbuild')
    self.rpm_fullname = kwargs.get('fullname', self.fullname)
    if kwargs.has_key('version'):
      self.rpm_version = kwargs['version']
    else:
      vermatch = VER_X_REGEX.match(self.version)
      if vermatch:
        self.rpm_version = vermatch.group(1)
      else:
        raise ValueError("Invalid version string; must contain at least one integer")

  def _build_rpm(self):
    self._check_release()
    self._build()
    self._save_release()
    self._add_output()

  def _add_output(self):
    self.DATA['output'].append(self.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
                               (self.rpm_name, self.rpm_version, self.rpm_release, self.rpm_arch))
    self.DATA['output'].append(self.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
                               (self.rpm_name, self.rpm_version, self.rpm_release))

  def _save_release(self):
    if self.autofile.exists():
      root_element = xmllib.tree.read(self.autofile).get('/distro')
    else:
      root_element = xmllib.tree.Element('distro')

    pva_element = xmllib.tree.uElement(self.pva, parent=root_element)
    rpms_element = xmllib.tree.uElement('rpms', parent=pva_element)
    parent_element = xmllib.tree.uElement(self.id, parent=rpms_element)
    release_element = xmllib.tree.uElement('release', parent=parent_element)

    release_element.text = self.rpm_release
    root_element.write(self.autofile)

    # set the mode and ownership of distro.conf.dat and distro.conf to
    # be the same.
    stat = self._config.file.stat()
    self.autofile.chown(stat.st_uid, stat.st_gid)
    self.autofile.chmod(stat.st_mode)

  def _check_release(self):
    if self.rpm_release == '0' or  \
           not self.autofile.exists() or \
           not self.mdfile.exists() or \
           self.diff.has_changed('input') or \
           self.diff.has_changed('variables') or \
           self.diff.has_changed('config'):
      self.rpm_release = str(int(self.rpm_release)+1)

  def _check_rpms(self):
    rpm = self.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
          (self.rpm_name, self.rpm_version, self.rpm_release, self.rpm_arch)
    srpm = self.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
           (self.rpm_name, self.rpm_version, self.rpm_release)
    self.cvars['custom-rpms'].append(rpm)
    self.cvars['custom-srpms'].append(srpm)

  def verify_rpm_exists(self):
    "rpm exists"
    rpm = self.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
          (self.rpm_name, self.rpm_version, self.rpm_release, self.rpm_arch)
    self.verifier.failUnless(rpm.exists(), "unable to find rpm at '%s'" % rpm)

  def verify_srpm_exists(self):
    "srpm exists"
    srpm = self.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
           (self.rpm_name, self.rpm_version, self.rpm_release)
    self.verifier.failUnless(srpm.exists(), "unable to find srpm at '%s'" % srpm)

  def _generate(self):   pass
  def _getiscript(self): return None
  def _getpscript(self): return None

  def _build(self):
    self.build_folder.mkdirs()
    self._generate()
    self._write_spec()
    self._write_manifest()
    self.log(1, L1("building %s-%s-%s.%s.rpm" % \
                   (self.rpm_name, self.rpm_version, self.rpm_release, self.rpm_arch)))
    mkrpm.build(self.build_folder, self.mddir, createrepo=False,
                bdist_base=self.bdist_base, rpm_base=self.rpm_base,
                dist_dir=self.dist_dir, keep_source=True,
                quiet=(self.logger.threshold < 5))

  def _write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'

    spec = ConfigParser()
    spec.add_section('pkg_data')
    spec.add_section('bdist_rpm')

    spec.set('pkg_data', 'name', self.rpm_name)
    spec.set('pkg_data', 'long_description', self.rpm_desc)
    spec.set('pkg_data', 'description', self.rpm_summary)

    spec.set('pkg_data', 'author', self.rpm_author)
    spec.set('pkg_data', 'version', self.rpm_version)

    spec.set('bdist_rpm', 'force_arch', self.rpm_arch)
    spec.set('bdist_rpm', 'distribution_name', self.rpm_fullname)

    spec.set('bdist_rpm', 'release', self.rpm_release)

    if self.rpm_provides:
      spec.set('bdist_rpm', 'provides',  ' '.join(self.rpm_provides))
    if self.rpm_requires:
      spec.set('bdist_rpm', 'requires',  ' '.join(self.rpm_requires))
    if self.rpm_obsoletes:
      spec.set('bdist_rpm', 'obsoletes', ' '.join(self.rpm_obsoletes))

    iscript = self._getiscript()
    pscript = self._getpscript()
    if iscript:
      spec.set('bdist_rpm', 'install_script', iscript)
    if pscript:
      spec.set('bdist_rpm', 'post_install', pscript)

    self._add_files(spec)

    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def _write_manifest(self):
    manifest = ['setup.py']
    manifest.extend( [ x.tokens[len(self.build_folder.tokens):] \
                       for x in self.build_folder.findpaths(type=pps.constants.TYPE_NOT_DIR) ] )
    (self.build_folder/'MANIFEST').write_lines(manifest)

  def _add_files(self, spec):
    # write the list of files to be installed and where they should be installed
    data_files = self._get_files()
    if not data_files:
      return

    value = []
    for installdir, files in data_files.items():
      value.append('%s : %s' %(installdir, ', '.join(files)))
    spec.set('pkg_data', 'data_files', '\n\t'.join(value))

    # mark files to be installed in '/etc' as config files
    config_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/etc'): # config files
        config_files.extend([ installdir/x.basename for x in data_files[installdir] ])
    if config_files:
      spec.set('bdist_rpm', 'config_files', '\n\t'.join(config_files))

    # mark files to be installed in '/usr/share/doc' as doc files
    doc_files = []
    for installdir in data_files.keys():
      if installdir.startswith('/usr/share/doc'):
        doc_files.extend([ installdir/x.basename for x in data_files[installdir] ])
    if doc_files:
      spec.set('bdist_rpm', 'doc_files', '\n\t'.join(doc_files))

  def _get_files(self):
    return {}


#---------- GLOBAL VARIABLES --------#
# each element for a distro's version, e.g. redhat/5, is a 3-tuple:
# (background color, font color, highlight color). To add an entry,
# look at the rhgb SRPM and copy the values from splash.c.
IMAGE_COLORS = {
  'CentOS': {
    '5.0': ('0x215593', '0xffffff', '0x1e518c'),
  },
  'Fedora Core': {
    '6': ('0x00254d', '0xffffff', '0x002044'),
  },
  'Fedora': {
    '7': ('0x001b52', '0xffffff', '0x1c2959'),
    '8': ('0x204b69', '0xffffff', '0x466e92'),
  },
  'Red Hat Enterprise Linux Server': {
    '5': ('0x781e1d', '0xffffff', '0x581715'),
  },
  '*': {
    '0': ('0x00254d', '0xffffff', '0x002044'),
  }
}
