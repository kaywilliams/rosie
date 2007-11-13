from ConfigParser import ConfigParser

import os

from dims import mkrpm
from dims import pps
from dims import sync
from dims import xmllib

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event, EventExit
from dimsbuild.logging   import L1
from dimsbuild.misc      import locals_imerge

__all__ = ['InputFilesMixin', 'LocalFilesMixin', 'ColorMixin', 'RpmBuildMixin']

P = pps.Path

class InputFilesMixin:
  def __init__(self):
    self.rpmdir = self.mddir/'rpm-input'

  def _setup_download(self):
    for k,v in self.installinfo.items():
      xpath, dst, defmode = v
      if xpath and self.config.xpath('%s' % xpath, None):
        default_dir = P(dst) / P(self.config.get(xpath).getparent().get('@dest', ''))
        for item in self.config.xpath('%s' % xpath, []):
          s = P(item.get('text()'))
          d = default_dir / P(item.get('@dest', ''))
          m = item.get('@mode', defmode)
          self.io.setup_sync(self.rpmdir / d.lstrip('/'), paths=[s], id=xpath, defmode=m)

  def _get_files(self):
    sources = {}
    for item in self.rpmdir.findpaths(type=pps.constants.TYPE_DIR, mindepth=1):
      sources[P(item[len(self.rpmdir):])] = item.findpaths(
                                            type=pps.constants.TYPE_NOT_DIR,
                                            mindepth=1, maxdepth=1)
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
  def __init__(self, rpmname, description, summary,
               defprovides=None, defobsoletes=None, defrequires=None):
    self.description  = description
    self.rpmname      = rpmname
    self.summary      = summary

    self.defobsoletes = defobsoletes
    self.defprovides  = defprovides
    self.defrequires  = defrequires

    self.autofile = P(self._config.file + '.dat')

  def _setup_build(self, **kwargs):
    if self.autofile.exists():
      self.release = xmllib.tree.read(self.autofile).get(
       '/distro/%s/rpms/%s/release/text()' % (self.pva, self.id), '0')
    else:
      self.release = '0'

    if self.config.get('@use-default-set', 'True'):
      self.obsoletes = self.defobsoletes
    else:
      self.obsoletes = ''
    if self.config.pathexists('obsoletes/package/text()'):
      self.obsoletes += ' ' + ' '.join(self.config.xpath(
                                  'obsoletes/package/text()'))
    if kwargs.has_key('obsoletes'):
      self.obsoletes += ' ' + kwargs['obsoletes']

    self.provides = self.obsoletes
    if self.defprovides:
      self.provides += ' ' + self.defprovides
    if kwargs.has_key('provides'):
      self.provides += ' ' + kwargs['provides']

    if self.defrequires:
      self.requires = self.defrequires
    else:
      self.requires = ''
    if self.config.pathexists('requires/package/text()'):
      self.requires += ' ' + ' '.join(self.config.xpath('requires/package/text()'))
    if kwargs.has_key('requires'):
      self.requires += ' ' + kwargs['requires']

    self.diff.setup(self.DATA)

    self.arch      = kwargs.get('arch',     'noarch')
    self.author    = kwargs.get('author',   'dimsbuild')
    self.fullname  = kwargs.get('fullname', self.fullname)
    self.version   = kwargs.get('version',  self.version)

  def _build_rpm(self):
    self._check_release()
    self._build()
    self._save_release()
    self._add_output()

  def _add_output(self):
    self.DATA['output'].append(self.mddir/'RPMS/%s-%s-%s.%s.rpm' % (self.rpmname,
                                                                    self.version,
                                                                    self.release,
                                                                    self.arch))
    self.DATA['output'].append(self.mddir/'SRPMS/%s-%s-%s.src.rpm' % (self.rpmname,
                                                                      self.version,
                                                                      self.release))

  def _save_release(self):
    if self.autofile.exists():
      root_element = xmllib.tree.read(self.autofile).get('/distro')
    else:
      root_element = xmllib.tree.Element('distro')

    pva_element     = xmllib.tree.uElement(self.pva,  parent=root_element)
    rpms_element    = xmllib.tree.uElement('rpms',    parent=pva_element)
    parent_element  = xmllib.tree.uElement(self.id,   parent=rpms_element)
    release_element = xmllib.tree.uElement('release', parent=parent_element)

    release_element.text = self.release
    root_element.write(self.autofile)

    # Bug 72. Make the distro.dat have the same ownership and
    # mode as the distro.conf
    stat = os.stat(self._config.file)
    os.chown(self.autofile, stat.st_uid, stat.st_gid)
    os.chmod(self.autofile, stat.st_mode)

  def _check_release(self):
    if self.release == '0' or  \
       not self.autofile.exists() or \
       not self.mdfile.exists() or \
       self.diff.has_changed('input') or \
       self.diff.has_changed('variables') or \
       self.diff.has_changed('config'):
      self.release = str(int(self.release)+1)

  def _test_build(self, default):
    # I imagine this isn't needed, since the module wont be loaded if enabled
    # is false...
    tobuild = self.config.get('/%s/@enabled' % self.id, default)
    if tobuild == 'default':
      return default in BOOLEANS_TRUE
    return tobuild in BOOLEANS_TRUE

  def _check_rpms(self):
    rpm = self.mddir/'RPMS/%s-%s-%s.%s.rpm' % (self.rpmname, self.version,
                                               self.release, self.arch)
    srpm = self.mddir/'SRPMS/%s-%s-%s.src.rpm' % (self.rpmname, self.version, self.release)
    self.cvars['custom-rpms'].append(rpm)
    self.cvars['custom-srpms'].append(srpm)

  def verify_rpm_exists(self):
    "rpm exists"
    rpm = self.mddir/'RPMS/%s-%s-%s.%s.rpm' % (self.rpmname, self.version,
                                               self.release, self.arch)
    self.verifier.failUnless(rpm.exists(), "unable to find rpm at '%s'" % rpm)

  def verify_srpm_exists(self):
    "srpm exists"
    srpm = self.mddir/'SRPMS/%s-%s-%s.src.rpm' % (self.rpmname, self.version, self.release)
    self.verifier.failUnless(srpm.exists(), "unable to find srpm at '%s'" % srpm)

  def _generate(self):   pass
  def _getiscript(self): return None
  def _getpscript(self): return None

  def _build(self):
    self.build_folder.mkdirs()
    self._generate()
    self._write_spec()
    self._write_manifest()
    self.log(1, L1("building %s-%s-%s.%s.rpm" % (self.rpmname, self.version,
                                                 self.release, self.arch)))
    mkrpm.build(self.build_folder,
                self.mddir,
                createrepo=False,
                keepTemp=True,
                quiet=(self.logger.threshold < 5))
    (self.build_folder/'dist').rm(recursive=True, force=True)

  def _write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'

    spec = ConfigParser()
    spec.add_section('pkg_data')
    spec.add_section('bdist_rpm')

    spec.set('pkg_data', 'name',             self.rpmname)
    spec.set('pkg_data', 'long_description', self.description)
    spec.set('pkg_data', 'description',      self.summary)

    spec.set('pkg_data', 'author',   self.author)
    spec.set('pkg_data', 'version',  self.version)

    spec.set('bdist_rpm', 'force_arch',        self.arch)
    spec.set('bdist_rpm', 'distribution_name', self.fullname)

    spec.set('bdist_rpm', 'release', self.release)

    if self.provides:  spec.set('bdist_rpm', 'provides',  self.provides)
    if self.requires:  spec.set('bdist_rpm', 'requires',  self.requires)
    if self.obsoletes: spec.set('bdist_rpm', 'obsoletes', self.obsoletes)

    iscript = self._getiscript()
    pscript = self._getpscript()
    if iscript: spec.set('bdist_rpm', 'install_script', iscript)
    if pscript: spec.set('bdist_rpm', 'post_install', pscript)

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
