from ConfigParser import ConfigParser
from os.path      import exists, join

import fcntl
import os
import rpm
import socket
import struct

from dims.osutils import *
from dims.sync    import sync

import dims.filereader as filereader
import dims.mkrpm      as mkrpm
import dims.shlib      as shlib
import dims.xmltree    as xmltree

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EventInterface
from dimsbuild.interface import DataModifyMixin, DiffMixin

#------ MIXINS ------#
class RpmsMixin:
  def __init__(self):
    self.LOCAL_REPO = join(self.METADATA_DIR, 'localrepo/')
  
  def addRpm(self, path):
    cp(path, self.LOCAL_REPO)
  
  def createrepo(self, path=None):
    path = path or self.LOCAL_REPO
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(cwd)

class ColorMixin:
  def __init__(self): pass

  def setColors(self, be=False, prefix='0x'):    
    # compute the background and foreground colors to use
    self.distroname, self.distroversion = self._get_distro_info()
    try:
      self.bgcolor, self.textcolor, self.hlcolor = IMAGE_COLORS[self.distroname][self.distroversion]
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

  def _get_distro_info(self):
    fullname = self.interface.cvars['source-vars']['fullname']    
    version = self.interface.cvars['source-vars']['version']
    return fullname, version


#---------- INTERFACES -----------#
class RpmsInterface(EventInterface, RpmsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)

  def buildRpm(self, path, rpm_output, changelog=None, logger='rpmbuild',
               createrepo=False, quiet=True):

    mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
                keepTemp=True, createrepo=createrepo,
                quiet=quiet)
    
    # need to delete the dist folder, because the RPMS have been copied
    # already to wherever they need to be. 
    rm(join(path, 'dist'), recursive=True, force=True)

  def getIpAddress(self, ifname='eth0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                        0x8915, # SIOCGIFADDR
                                        struct.pack('256s', ifname[:15]))[20:24])  


#---------- HANDLERS -------------#
class RpmsHandler(DiffMixin, DataModifyMixin):
  def __init__(self, interface, data, id, rpmname,
               description=None, long_description=None):

    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface

    # self.<k> = self.interface.<v>
    for k,v in [('config', 'config'), ('fullname', 'fullname'),
                ('arch', 'basearch'), ('software_store', 'SOFTWARE_STORE'),
                ('fullname', 'fullname'), ('product', 'product'),
                ('version', 'version'), ('metadata', 'METADATA_DIR'), ('log', 'log')]:
      setattr(self, k, getattr(self.interface, v))

    self.sharepath = self.interface._base.sharepath

    self.id = id
    self.rpmname = rpmname
    self.description = description
    self.long_description = long_description
    self.author = 'dimsbuild'

    self.output_location = join(self.metadata, self.id)
    self.autoconf = join(dirname(self.config.file), 'distro.conf.auto')

    DiffMixin.__init__(self, join(self.metadata, '%s.md' % self.id), data)
    DataModifyMixin.__init__(self)

  def setup(self):
    self.addOutput(self.output_location)
    self.addOutput(join(self.interface.LOCAL_REPO, 'RPMS',
                        '%s*[!Ss][!Rr][!Cc].[Rr][Pp][Mm]' % self.rpmname))
    self.addOutput(join(self.interface.LOCAL_REPO, 'SRPMS',
                        '%s*[Ss][Rr][Cc].[Rr][Pp][Mm]' % self.rpmname))
    
  def force(self):
    self._clean()
    
  def check(self):
    if self._test_build():      
      if self.test_diffs(): self._clean(); return True
      else: return False
    else:
      self._clean(); return False
  
  def run(self):
    self.log(0, "building %s rpm" %(self.rpmname,))
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)    
    self._copy()
    self._generate()
    self._write_spec()
    self.interface.buildRpm(self.output_location, self.interface.LOCAL_REPO,
                            quiet=(self.interface.logthresh < 4))
    if not self._valid():
      raise OutputInvalidError("'%s' output invalid" %(self.rpmname,))
    self.write_metadata()    

  def apply(self, type='mandatory', requires=None):
    missingrpms = [ x for x in self._find_rpms() if not exists(x) ]

    if len(missingrpms) != 0:
      if self._test_build() and not self.interface.isSkipped(self.id):
        raise RuntimeError("missing rpm(s): " %(', '.join(missingrpms)))
      else:
        return # the rpm hasn't been created, therefore nothing else to do here

    # add rpms to the included-packages control var, so that they are
    # added to the comps.xml
    if not self.interface.cvars['included-packages']:
      self.interface.cvars['included-packages'] = []
    self.interface.cvars['included-packages'].append((self.rpmname, type, requires))

    obsoletes = self._get_obsoletes()
    if obsoletes is not None:
      if not self.interface.cvars['excluded-packages']:
        self.interface.cvars['excluded-packages'] = []
      self.interface.cvars['excluded-packages'].extend(obsoletes.split())

  def _clean(self):
    for rpm in self._find_rpms():
      self.removeOutput(rpm)
      rm(rpm, force=True)
    rm(self.output_location, recursive=True, force=True)
    rm(self.mdfile, force=True)    

  def _test_build(self):
    return self.config.get('/distro/rpms/%s/create/text()' %(self.id,), 'True') in BOOLEANS_TRUE

  def _find_rpms(self, prefix=True):
    v,r,a = self._read_autoconf()
    rpm = join('RPMS', '%s-%s-%s.%s.rpm' %(self.rpmname, v, r, a))
    srpm = join('SRPMS', '%s-%s-%s.src.rpm' %(self.rpmname, v, r))    

    if prefix:
      rpm = join(self.interface.LOCAL_REPO, rpm)
      srpm = join(self.interface.LOCAL_REPO, srpm)

    return [rpm, srpm]
  
  def _copy(self):
    if self.data.has_key('input'):
      for file in self.data['input']:
        sync(file, self.output_location)
  
  def _write_spec(self):
    self._create_manifest()
    setup_cfg = join(self.output_location, 'setup.cfg')
    if exists(setup_cfg): return
    
    version, release, arch = self._read_autoconf()

    parser = ConfigParser()    
    parser.add_section('pkg_data')        
    parser.set('pkg_data', 'name', self.rpmname)
    parser.set('pkg_data', 'version', version)
    parser.set('pkg_data', 'long_description', self.long_description)
    parser.set('pkg_data', 'description', self.description)
    parser.set('pkg_data', 'author', self.author)

    data_files = self._get_data_files()
    if data_files is not None:
      parser.set('pkg_data', 'data_files', data_files)
    
    parser.add_section('bdist_rpm')
    parser.set('bdist_rpm', 'distribution_name', self.fullname)
    
    release = str(int(release) + 1)
    parser.set('bdist_rpm', 'release', release)

    parser.set('bdist_rpm', 'force_arch', arch)

    self.log(1, "release number: %s" % release)
    
    for tag in ['config_files', 'doc_files', 'install_script', 'obsoletes',
                'post_install', 'provides', 'requires']:
      attr = '_get_%s' %tag
      if hasattr(self, attr):
        value = getattr(self, attr)()
        if value is not None:
          parser.set('bdist_rpm', tag, value)

    self._write_autoconf(release=release)
    
    f = open(setup_cfg, 'w')
    parser.write(f)
    f.close()

  def _read_autoconf(self):
    if exists(self.autoconf):
      root = xmltree.read(self.autoconf)
      package = root.get('//distro-auto/%s' %self.id, None)
      if package is not None:
        v = package.get('version/text()', self.version)
        r = package.get('release/text()', '0')
        a = package.get('arch/text()', self._get_force_arch())
        return v, r, a
    return self.version, '0', self._get_force_arch()

  def _write_autoconf(self, version=None, release=None, arch=None):
    if exists(self.autoconf):
      root = xmltree.read(self.autoconf)
      package = root.get('//distro-auto/%s' %self.id, None)
      if package is None:
        package = xmltree.Element(self.id, parent=root)

      if version is not None:
        v = package.get('version', None)
        if v is None:
          v = xmltree.Element('version', parent=package)
        v.text = version

      if release is not None:
        r = package.get('release', None)
        if r is None:
          r = xmltree.Element('release', parent=package)
        r.text = release
        
      if arch is not None:
        a = package.get('arch', None)
        if a is None:
          a = xmltree.Element('arch', parent=package)
        a.text = arch
    else:
      root = xmltree.Element('distro-auto')
      package = xmltree.Element(self.id, parent=root)
      if version is not None:
        v = xmltree.Element('version', parent=package, text=version)
      if release is not None:
        r = xmltree.Element('release', parent=package, text=release)
      if arch is not None:
        a = xmltree.Element('arch', parent=package, text=arch)
    
    root.write(self.autoconf)
  
  def _create_manifest(self): pass        
  def _generate(self):        pass
  
  def _get_config_files(self):   return None
  def _get_data_files(self):     return None
  def _get_doc_files(self):      return None
  def _get_force_arch(self):     return 'noarch'
  def _get_install_script(self): return None    
  def _get_obsoletes(self):      return None  
  def _get_post_install(self):   return None
  def _get_provides(self):       return None
  def _get_requires(self):       return None
  def _valid(self):              return True

  def _cache_input(self, info=[], prefix=None):
    rtn = []
    prefix = prefix or dirname(self.config.file)
    for dir, xquery in info:
      sources = []
      for source in self.interface.config.xpath(xquery, []):
        if not source.startswith('/') and source.find('://') == -1: # relative path
          source = join(prefix, source)
        sources.append(source)

      if sources:
        dst = join(self.output_location, dir)
        if not exists(dst):
          mkdir(dst, parent=True)
        sync(sources, dst)
        rtn.extend(find(location=join(self.output_location, dir), name='*'))
    return rtn

class OutputInvalidError(IOError): pass

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
  },
  'Red Hat Enterprise Linux Server': {
    '5': ('0x781e1d', '0xffffff', '0x581715'),
  },
  '*': {
    '0': ('0x00254d', '0xffffff', '0x002044'),
  }
}
