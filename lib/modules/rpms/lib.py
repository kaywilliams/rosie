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

from event     import EventInterface
from interface import DiffMixin
from main      import BOOLEANS_TRUE

#--------------- FUNCTIONS ------------------#
def getIpAddress(ifname='eth0'):
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                      0x8915, # SIOCGIFADDR
                                      struct.pack('256s', ifname[:15]))[20:24])


def buildRpm(path, rpm_output, changelog=None, logger='rpmbuild',
             functionName='main', createrepo=False, quiet=True):
  eargv = ['--bdist-base', '/usr/src/redhat',
           '--rpm-base', '/usr/src/redhat/']
  
  mkrpm.build(path, rpm_output, changelog=changelog, logger=logger,
              functionName=functionName, keepTemp=True, createrepo=createrepo,
              quiet=quiet, eargv=eargv)
  
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


#---------- INTERFACES -----------#
class RpmsInterface(EventInterface, RpmsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)


#---------- HANDLERS -------------#
class RpmsHandler(DiffMixin):
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

    self.obsoletes = self.config.get('//%s/obsoletes/text()' % self.elementname, None)
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
    self.sharepath = self.interface._base.sharepath
    
    self.log = self.interface.log

    # get the rpms and srpms to be a part of the output too
    data['output'].extend(find(self.rpm_output, name='%s*' %(self.rpmname,)))

    DiffMixin.__init__(self, join(self.metadata, '%s.md' % self.elementname), data)

  def clean_output(self):
    for rpm in find(self.rpm_output, name='%s*[Rr][Pp][Mm]' %(self.rpmname,)):
      rm(rpm, force=True)
    rm(self.output_location, recursive=True, force=True)

  def force(self):
    self.clean_output()

  def test_build_rpm(self):
    return not self.interface.isSkipped(self.eventid) and \
           (self.interface.isForced(self.eventid) or \
            self.config.get('//%s/create/text()' %(self.elementname,), 'True') in BOOLEANS_TRUE)
  
  def check(self):
    if self.test_build_rpm() and (self.test_diffs() or not self.output_valid()):
      self.clean_output()
      return True
    return False
  
  def run(self):
    self.log(0, "creating '%s' rpm" %(self.rpmname,))
    self.get_input()
    self.add_output()

    if not self.output_valid():
      raise OutputInvalidError("%s RPM output is invalid" %(self.rpmname,))

    # remove all the rpm and srpms from data['output'] and add new ones
    self.data['output'].extend(find(self.rpm_output, name='%s*' %(self.rpmname,)))
    
    self.write_metadata()
    
    # input store has changed because a new rpm has been created
    self.interface.cvars['input-store-changed'] = True
    
    # HACK ALERT: need to the remove the .depsolve/dimsbuild-local folder so
    # that depsolver picks up the new RPM.
    depsolver_cache = join(self.interface.METADATA_DIR, '.depsolve', 'dimsbuild-local')
    if exists(depsolver_cache):
      rm(depsolver_cache, recursive=True, force=True)      

  def apply(self, type='mandatory', requires=None):    
    try:
      find(join(self.interface.METADATA_DIR, 'localrepo', 'RPMS'),
           name='%s*.[Rr][Pp][Mm]' %(self.rpmname,), prefix=False)[0]

      # add rpms to the included-packages control var, so that
      # they are added to the comps.xml
      if not self.interface.cvars['included-packages']:
        self.interface.cvars['included-packages'] = []
      self.interface.cvars['included-packages'].append((self.rpmname, type, requires))
      
      if self.obsoletes is not None:
        if not self.interface.cvars['excluded-packages']:
          self.interface.cvars['excluded-packages'] = []
        self.interface.cvars['excluded-packages'].extend(self.obsoletes.split())
    except IndexError:
      if self.test_build_rpm():
        raise RuntimeError("missing rpm: '%s'" %(self.rpmname,))
    
  def output_valid(self): return True
  
  def get_input(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)
    if self.data.has_key('input'):
      for input in self.data['input']:
        sync(input, self.output_location)

  def add_output(self):
    self.generate()
    self.setup()
    buildRpm(self.output_location, self.rpm_output,
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
    if self.provides is not None:
      parser.set('bdist_rpm', 'provides', self.provides)
    if self.obsoletes is not None:
      parser.set('bdist_rpm', 'obsoletes', self.obsoletes)
    if self.requires is not None:
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

    newrelease = None
    ad = None

    if exists(autoconf):
      root = xmltree.read(autoconf)
    else:
      root = xmltree.Element('auto')

    package = root.get('//%s' %self.elementname, None) or \
              xmltree.Element(self.elementname, parent=root)
    release = package.get('release', None)

    if release is not None:      
      oldrelease = release.text
    else:
      release = xmltree.Element('release', parent=package)
      oldrelease = '0'
    
    newrelease = str(int(oldrelease) + 1)

    release.text = newrelease
    root.write(autoconf)
    
    self.log(1, "'%s' release number: %s" %(self.elementname, newrelease,))
    return newrelease


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
