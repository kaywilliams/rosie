import fcntl
import os
import rpm
import socket
import struct

import dims.filereader as filereader
import dims.mkrpm      as mkrpm
import dims.shlib      as shlib
import dims.xmltree    as xmltree

from ConfigParser import ConfigParser
from dims.osutils import basename, dirname, find, mkdir, rm
from dims.sync    import sync
from event        import EventInterface
from main         import BOOLEANS_TRUE
from os.path      import exists, join
from output       import OutputEventHandler, OutputInvalidError

#--------------- FUNCTIONS ------------------#
def getIpAddress(ifname='eth0'):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                      0x8915, # SIOCGIFADDR
                                      struct.pack('256s', ifname[:15]))[20:24])
                                      
def build_rpm(path, rpm_output, changelog=None, logger='rpmbuild',
             functionName='main', keepTemp=True, createrepo=False,
             quiet=True):
  # keepTemp should be True if path points to a location inside
  # the builddata/ folder, because if keepTemp is False, path
  # is going to get deleted once the rpm build process is complete.
  eargv = ['--bdist-base', '/usr/src/redhat',
           '--rpm-base', '/usr/src/redhat/']
  
  mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
              functionName=functionName, keepTemp=keepTemp, createrepo=createrepo,
              quiet=quiet, eargv=eargv)
  
  # need to delete the dist folder, because the RPMS have been copied
  # already to wherever they need to be. 
  rm(join(path, 'dist'), recursive=True, force=True)


#------ INTERFACES/MIXINS ------#
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
    if type(color) == tuple:
      return self._color_to_bigendian(color[0]), self._color_to_bigendian(color[1])
    else:
      return self._color_to_bigendian(color)

  def _color_to_bigendian(self, color):
    if color.startswith('0x'):
      color = color[2:]
    color = '%s%s' % ((6-len(color))*'0', color) # prepend zeroes to color
    return int('0x%s%s%s' % (color[4:], color[2:4], color[:2]), 16)

  def _get_distro_info(self):
    import re
    scan = re.compile('.*/(.*)-release-([\d]).*\.[Rr][Pp][Mm]')
    distro, version = None, None
    fl = filereader.read(self.verfile)
    for rpm in fl:
      match = scan.match(rpm)
      if match:
        try:
          distro = match.groups()[0]
          version = match.groups()[1]
        except (AttributeError, IndexError), e:
          raise ValueError, "Unable to compute release version from distro metadata"
        break
    if distro is None or version is None:
      raise ValueError, "Unable to compute release version from distro metadata"
    return (distro, version[0])


class RpmsInterface(EventInterface, RpmsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)

  def append_cvar(self, flag, value):
    if flag in self._base.cvars.keys():
      if type(value) == list:
        self._base.cvars[flag].extend(value)
      else:
        self._base.cvars[flag].append(value)
    else:
      if type(value) == list:
        self._base.cvars[flag] = value
      else:
        self._base.cvars[flag] = [value]
        

#---------- HANDLERS -------------#
class RpmHandler(OutputEventHandler):
  def __init__(self, interface, data, elementname=None, rpmname=None,
               provides=None, provides_test=None, obsoletes=None, requires=None,
               description=None, long_description=None):
    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface    
    self.config = self.interface.config
    self.metadata = self.interface.METADATA_DIR
    self.software_store = self.interface.SOFTWARE_STORE
    self.arch = self.interface.basearch    
    self.rpm_output = join(self.metadata, 'localrepo/')

    self.fullname = self.config.get('//main/fullname/text()')
    self.product = self.config.get('//main/product/text()')
    self.version = self.config.get('//main/version/text()')

    self.elementname = elementname
    self.rpmname = rpmname
    self.provides = provides
    self.provides_test = provides_test

    self.obsoletes = self.config.get('//%s/obsoletes/text()' %(self.elementname,), None)
    if self.config.get('//%s/obsoletes/@use-default-set' %(self.elementname,), 'True') in BOOLEANS_TRUE:
      if self.obsoletes is not None:
        self.obsoletes = ' '.join([self.obsoletes.strip(), obsoletes])
      else:
        self.obsoletes = obsoletes

    self.requires = requires    
    self.description = description
    self.long_description = long_description
    self.author = 'dimsbuild'
    self.output_location = join(self.metadata, self.elementname)
    self.share_path = self.interface._base.sharepath
    
    self.log = self.interface.log
         
    self._set_method()
    
    OutputEventHandler.__init__(self, self.config, data,
                                mdfile=join(self.metadata, '%s.md' % self.elementname))
        
  def _set_method(self):
    if self.config.get('//%s/create/text()' % self.elementname, 'True') in BOOLEANS_TRUE:
      self.create = True
    else:
      self.create = False

  def clear_output(self):
    for rpm in find(self.rpm_output, name='%s*[Rr][Pp][Mm]' %(self.rpmname,)):
      rm(rpm, force=True)
    rm(self.output_location, recursive=True, force=True)

  def force(self):
    self.clear_output()
  
  def run(self):
    if self.test_input_changed() or not self.test_output_valid():
      self.clear_output()
    else:
      return
    self.get_input()
    self.add_output()
    if not self.test_output_valid():
      raise OutputInvalidError, "output is invalid"
    self.write_metadata()
    if self.create:
      self.interface.set_cvar('input-store-changed', True)
      # need to the remove the .depsolve/dimsbuild-local folder so
      # that depsolver picks up the new RPM.
      depsolver_cache = join(self.interface.METADATA_DIR, '.depsolve', 'dimsbuild-local')
      if exists(depsolver_cache):
        rm(depsolver_cache, recursive=True, force=True)      

  def apply(self):    
    try:
      find(join(self.interface.METADATA_DIR, 'localrepo', 'RPMS'),
           name='%s*.[Rr][Pp][Mm]' %(self.rpmname,), prefix=False)[0]
      # add rpms to the included-packages control var, so that
      # they are added to the comps.xml
      self.interface.append_cvar('included-packages', [self.rpmname])
      if self.obsoletes is not None:
        self.interface.append_cvar('excluded-packages', self.obsoletes.split())        
    except IndexError:
      if self.create:
        raise RuntimeError("missing rpm: '%s'" %(self.rpmname,))
    
  def test_output_valid(self): return True
  
  def get_input(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)
    if self.create and self.data.has_key('input'):
      for input in self.data['input']:
        sync(input, self.output_location)

  def add_output(self):
    if self.create:
      self.generate()
      self.setup()
      build_rpm(self.output_location, self.rpm_output,
                quiet=(self.interface.logthresh < 4)) # piping rpmbuild output to loglevel 4
    
  def generate(self): pass

  def setup(self):
    self.create_manifest()
    setup_cfg = join(self.output_location, 'setup.cfg')
    if exists(setup_cfg):
      return
    parser = ConfigParser()
    
    parser.add_section('pkg_data')        
    parser.set('pkg_data', 'name', self.rpmname)
    parser.set('pkg_data', 'version', self.version)
    parser.set('pkg_data', 'long_description', self.long_description)
    parser.set('pkg_data', 'description', self.description)
    parser.set('pkg_data', 'author', self.author)
    data_files = self.get_data_files()
    if data_files is not None:
      parser.set('pkg_data', 'data_files', data_files)
    
    parser.add_section('bdist_rpm')
    parser.set('bdist_rpm', 'release', self.get_release_number())
    parser.set('bdist_rpm', 'distribution_name', self.fullname)
    if self.provides is not None and len(self.provides.strip()) > 0:
      parser.set('bdist_rpm', 'provides', self.provides)
    if self.obsoletes is not None and len(self.obsoletes.strip()) > 0:
      parser.set('bdist_rpm', 'obsoletes', self.obsoletes)
    if self.requires is not None and len(self.requires.strip()) > 0:
      parser.set('bdist_rpm', 'requires', self.requires)

    post_install_script = self.get_post_install_script() 
    if post_install_script is not None:
      parser.set('bdist_rpm', 'post_install', post_install_script)

    install_script = self.get_install_script()
    if install_script is not None:
      parser.set('bdist_rpm', 'install_script', install_script)
      
    f = open(setup_cfg, 'w')
    parser.write(f)
    f.close()

  def create_manifest(self): pass

  def get_install_script(self):      return None    
  def get_post_install_script(self): return None
  def get_data_files(self):          return None
  
  def get_release_number(self):
    autoconf = join(dirname(self.config.file), 'distro.conf.auto')

    new_release = None
    ad = None

    if exists(autoconf):
      ad = xmltree.read(autoconf)
      root = ad.getroot()
      old_release = root.iget('//%s/release/text()' %(self.elementname,))
      if old_release:
        new_release = str(int(old_release)+1)
        create_package = root.iget('//%s' %(self.elementname,))
        # FIXME: raise exception if not found? We are creating this file, so maybe
        # it's OK to not raise an exception 
        create_package.remove(root.get('//%s/release' %(self.elementname,), [])[0]) 
        
    if not new_release:
      if ad:
        document_root = ad.getroot()
      else:
        document_root = xmltree.Element('auto')
        ad = xmltree.XmlTree(document_root)
      create_package = xmltree.Element(self.elementname, parent=document_root)            
      new_release = '1'
      
    xmltree.Element('release', parent=create_package, text=new_release)            
    ad.write(autoconf)
    self.log(1, "'%s' release number: %s" %(self.elementname, new_release,))
    return new_release


# each element for a distro's version, e.g. redhat/5, is a 3-tuple:
# (background color, font color, highlight color). To add an entry,
# look at the rhgb SRPM and copy the values from splash.c.
IMAGE_COLORS = {
  'centos': {
    '5': ('0x215593', '0xffffff', '0x1e518c'),
  },
  'fedora': {
    '6': ('0x00254d', '0xffffff', '0x002044'),
    '7': ('0x001b52', '0xffffff', '0x1c2959'),
  },
  'redhat': {
    '5': ('0x781e1d', '0xffffff', '0x581715'),
  },
  '*': {
    '0': ('0x00254d', '0xffffff', '0x002044'),
  }
}
