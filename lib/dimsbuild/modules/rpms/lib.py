from ConfigParser import ConfigParser
from os.path      import exists, join

import fcntl
import os
import rpm
import socket
import struct

from dims.osutils import basename, dirname, find, mkdir, rm
from dims.sync    import sync

import dims.filereader as filereader
import dims.mkrpm      as mkrpm
import dims.shlib      as shlib
import dims.xmltree    as xmltree

from constants import BOOLEANS_TRUE
from difftest  import expand
from event     import EventInterface
from interface import DiffMixin

#--------------- FUNCTIONS ------------------#
def getIpAddress(ifname='eth0'):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                      0x8915, # SIOCGIFADDR
                                      struct.pack('256s', ifname[:15]))[20:24])


def buildRpm(path, rpm_output, changelog=None, logger='rpmbuild',
             functionName='main', createrepo=False, quiet=True):

  mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
              functionName=functionName, keepTemp=True, createrepo=createrepo,
              quiet=quiet)
  
  # need to delete the dist folder, because the RPMS have been copied
  # already to wherever they need to be. 
  rm(join(path, 'dist'), recursive=True, force=True)


#------ MIXINS ------#
class RpmsMixin:
  def __init__(self):
    self.LOCAL_REPO = join(self.METADATA_DIR, 'localrepo/')
  
  def addRpm(self, path):
    cp(path, self.LOCAL_REPO)
  
  def createrepo(self):
    pwd = os.getcwd()
    os.chdir(self.LOCAL_REPO)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)  


class ColorMixin:
  def __init__(self, verfile):
    self.verfile = verfile

  def set_colors(self):
    # compute the background and foreground colors to use
    self.distroname, self.distroversion = self._get_distro_info()
    try:
      self.bgcolor, self.textcolor, self.hlcolor = IMAGE_COLORS[self.distroname][self.distroversion]
    except KeyError:
      self.bgcolor, self.textcolor, self.hlcolor = IMAGE_COLORS['*']['0']    
    
  def color_to_bigendian(self, color):
    if color.startswith('0x'):
      color = color[2:]
    color = '%s%s' % ((6-len(color))*'0', color) # prepend zeroes to color
    return int('0x%s%s%s' % (color[4:], color[2:4], color[:2]), 16)

  def _get_distro_info(self):
    fullname = self.interface.cvars['source-vars']['fullname']    
    version = self.interface.cvars['source-vars']['version']
    return fullname, version


#---------- INTERFACES -----------#
class RpmsInterface(EventInterface, RpmsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)


#---------- HANDLERS -------------#
class RpmsHandler(DiffMixin):
  def __init__(self, interface, data, id, rpmname,
               description=None, long_description=None):

    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface    
    self.config = self.interface.config
    self.metadata = self.interface.METADATA_DIR
    self.software_store = self.interface.SOFTWARE_STORE
    self.arch = self.interface.basearch    
    self.rpm_output = self.interface.LOCAL_REPO

    self.fullname = self.config.get('//main/fullname/text()')
    self.product = self.config.get('//main/product/text()')
    self.version = self.config.get('//main/version/text()')

    self.id = id
    self.rpmname = rpmname

    self.description = description
    self.long_description = long_description
    self.author = 'dimsbuild'

    self.output_location = join(self.metadata, self.id)
    self.sharepath = self.interface._base.sharepath
    
    self.log = self.interface.log
    self.autoconf = join(dirname(self.config.file), 'distro.conf.auto')

    DiffMixin.__init__(self, join(self.metadata, '%s.md' % self.id), data)

  def clean_output(self):
    rm(self.output_location, recursive=True, force=True)
    for x in self._find_rpms():
      if self.data.has_key('output') and x in self.data['output']:
        self.data['output'].remove(x)
      if exists(x):
        rm(x, force=True)
    rm(self.mdfile, force=True)

  def force(self):
    self._modify_output_data()
    self.clean_output()
      
  def check(self):
    self._modify_output_data()
    if self.test_build_rpm():
      if self.test_diffs():
        self.clean_output()
        return True
      else:
        return False
    else:
      self.clean_output()
      return False
  
  def run(self):
    self.log(0, "creating '%s' rpm" %(self.rpmname,))
    self.init()
    self.copy()
    self.create()
    if not self.output_valid():
      raise OutputInvalidError("'%s' output invalid" %(self.rpmname,))
    self._modify_output_data()
    self.write_metadata()
    
  def apply(self, type='mandatory', requires=None):
    missingrpms = [ x for x in self._find_rpms() if not exists(x) ]

    if len(missingrpms) != 0:
      if self.test_build_rpm() and not self.interface.isSkipped(self.id):
        raise RuntimeError("missing rpm(s): " %(', '.join(missingrpms)))
      else:
        return # the rpm hasn't been created, therefore nothing else to do here

    # add rpms to the included-packages control var, so that
    # they are added to the comps.xml
    if not self.interface.cvars['included-packages']:
      self.interface.cvars['included-packages'] = []
    self.interface.cvars['included-packages'].append((self.rpmname, type, requires))

    obsoletes = self._get_obsoletes()
    if obsoletes is not None:
      if not self.interface.cvars['excluded-packages']:
        self.interface.cvars['excluded-packages'] = []
      self.interface.cvars['excluded-packages'].extend(obsoletes.split())
  
  def init(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)

  def copy(self):
    if self.data.has_key('input'):
      for input in self.data['input']:
        sync(input, self.output_location)

  def create(self):
    self._generate()
    self._setup()
    buildRpm(self.output_location, self.rpm_output,
             quiet=(self.interface.logthresh < 4)) # piping rpmbuild output to loglevel 4
    
  def test_build_rpm(self):
    return self.config.get('//%s/create/text()' %(self.id,), 'True') in BOOLEANS_TRUE

  def _find_rpms(self, prefix=True):
    v, r, a = self._read_autoconf()
    rpm = join('RPMS', '%s-%s-%s.%s.rpm' %(self.rpmname, v, r, a))
    srpm = join('SRPMS', '%s-%s-%s.src.rpm' %(self.rpmname, v, r))    

    if prefix:
      rpm = join(self.rpm_output, rpm)
      srpm = join(self.rpm_output, srpm)

    return [rpm, srpm]
  
  def _modify_output_data(self):
    if not self.data.has_key('output'):
      assert 'output' not in self.handlers.keys()
      self.data['output'] = []
      h = OutputHandler(self.data['output'])
      self.DT.addHandler(h)
      self.handlers[key] = h
    
    rpms = self._find_rpms()
    for rpm in rpms:
      if rpm not in self.data['output']:
        self.data['output'].append(rpm)
    
  def output_valid(self): return True
  
  def _generate(self): pass
  
  def _setup(self):
    self._create_manifest()
    setup_cfg = join(self.output_location, 'setup.cfg')
    if exists(setup_cfg):
      return
    parser = ConfigParser()

    version, release, arch = self._read_autoconf()

    parser.add_section('global')
    parser.set('global', 'verbose', '0')
    
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

    self.log(1, "%s rpm: release=%s" %(self.rpmname, release))
    
    for tag in ['provides', 'requires', 'obsoletes', 'post_install', 'install_script']:
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

  def _get_force_arch(self):     return 'noarch'
  def _get_data_files(self):     return None
  def _get_install_script(self): return None    
  def _get_obsoletes(self):      return None  
  def _get_post_install(self):   return None
  def _get_provides(self):       return None
  def _get_requires(self):       return None


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
