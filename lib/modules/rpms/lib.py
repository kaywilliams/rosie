import fcntl
import os
import rpm
import socket
import struct

import dims.mkrpm as mkrpm
import dims.shlib as shlib
import dims.xmltree as xmltree

from ConfigParser import ConfigParser
from dims.osutils import basename, dirname, find, mkdir, rm
from dims.sync import sync
from event import EventInterface
from main import BOOLEANS_TRUE
from os.path import exists, join
from output import OutputEventHandler, OutputInvalidError


#--------------- FUNCTIONS ------------------#
def getProvides(rpmPath):
  "Returns the list of items provided by the RPM specified by rpmPath."
  ts = rpm.TransactionSet()
  fd = os.open(rpmPath, os.O_RDONLY)
  h = ts.hdrFromFdno(fd)
  del ts
  provides = h['providename']    
  os.close(fd)
  return provides    

def getIpAddress(ifname='eth0'):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                      0x8915, # SIOCGIFADDR
                                      struct.pack('256s', ifname[:15]))[20:24])
                                      
def buildRpm(path, rpm_output, changelog=None, logger='rpmbuild',
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
    self.LOCAL_REPO = join(self.getMetadata(), 'localrepo/')
  
  def addRpm(self, path):
    cp(path, self.LOCAL_REPO)
  
  def createrepo(self):
    pwd = os.getcwd()
    os.chdir(self.LOCAL_REPO)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)  

class RpmsInterface(EventInterface, RpmsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)

  def append_cvar(self, flag, value):
    if flag in self._base.mvars.keys():
      if type(value) == list:
        self._base.mvars[flag].extend(value)
      else:
        self._base.mvars[flag].append(value)
    else:
      if type(value) == list:
        self._base.mvars[flag] = value
      else:
        self._base.mvars[flag] = [value]

#---------- HANDLERS -------------#
class RpmHandler(OutputEventHandler):
  def __init__(self, interface, data, elementname=None, rpmname=None,
               provides=None, provides_test=None, obsoletes=None, requires=None,
               description=None, long_description=None):
    if len(data['output']) > 1:
      raise Exception, "only one item should be specified in data['output']"
        
    self.interface = interface    
    self.config = self.interface.config
    self.metadata = self.interface.getMetadata()
    self.software_store = self.interface.getSoftwareStore()
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
      if self.obsoletes:
        self.obsoletes = ' '.join([self.obsoletes, obsoletes])
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
  
  def pre(self):
    if self.test_input_changed() or not self.testOutputValid():
      for rpm in find(self.rpm_output, name='%s*[Rr][Pp][Mm]' % self.rpmname):
        rm(rpm, force=True)
      rm(self.output_location, recursive=True, force=True)
      return True
    return False
    
  def modify(self):
    self.getInput()
    self.addOutput()
    if not self.testOutputValid():
      raise OutputInvalidError, "output is invalid"
    self.write_metadata()

  def testOutputValid(self): return True
  
  def getInput(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)
    if self.create and self.data.has_key('input'):
      for input in self.data['input']:
        sync(input, self.output_location)

  def addOutput(self):
    if self.create:
      self.generate()
      self.setup()
      buildRpm(self.output_location, self.rpm_output,
               quiet=(self.interface.logthresh < 4)) # piping rpmbuild output to loglevel 4

  def generate(self): pass
  
  def setup(self):
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
    if data_files:
      parser.set('pkg_data', 'data_files', data_files)
    
    parser.add_section('bdist_rpm')
    parser.set('bdist_rpm', 'release', self.get_release())
    parser.set('bdist_rpm', 'distribution_name', self.fullname)
    if self.provides:
      parser.set('bdist_rpm', 'provides', self.provides)
    if self.obsoletes:
      parser.set('bdist_rpm', 'obsoletes', self.obsoletes)
    if self.requires:
      parser.set('bdist_rpm', 'requires', self.requires)

    post_install_script = self.get_post_install_script() 
    if post_install_script:
      parser.set('bdist_rpm', 'post_install', post_install_script)

    install_script = self.get_install_script()
    if install_script:
      parser.set('bdist_rpm', 'install_script', install_script)
    f = open(setup_cfg, 'w')
    parser.write(f)
    f.close()

  def get_install_script(self):      return None    
  def get_post_install_script(self): return None
  def get_data_files(self):          return None
  
  def get_release(self):
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
        # TODO: raise exception if not found? We are creating this file, so maybe
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

