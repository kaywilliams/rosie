import os
import tempfile

from os.path            import join, exists, isdir, isfile
from rpmUtils.miscutils import rpm2cpio

import dims.shlib as shlib

from dims.imglib  import CpioImage
from dims.osutils import *
from dims.sync    import sync

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface
from main      import BOOLEANS_TRUE
from magic     import FILE_TYPE_LSS
from output    import OutputEventHandler, OutputEventMixin, tree

try:
  import Image
except ImportError:
  raise ImportError, "missing 'python-imaging' rpm"

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'installer_logos',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['installer-logos', 'splash.lss'],
    'requires': ['software'],
    'parent': 'INSTALLER',
  },
  {
    'id': 'installer_release_files',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['installer-release-files'],
    'requires': ['software'],
    'parent': 'INSTALLER',
  },  
]

#-------- HANDLER DICTIONARY ---------#
# dictionary of semi-permanent handlers so that I can keep one instance
# around between two hook functions
HANDLERS = {}
def addHandler(handler, key): HANDLERS[key] = handler
def getHandler(key): return HANDLERS[key]


#-------- HELPER FUNCTIONS -----------#
def extractRpm(rpmPath, output=os.getcwd()):
  """ 
  Extract the contents of the RPM file specified by rpmPath to
  the output location. The rpmPath parameter can use globbing.
  
  @param rpmPath : the path to the RPM file    
  @param output  : the directory that is going to contain the RPM's
  contents
  """
  dir = tempfile.mkdtemp()
  filename = join(dir, 'rpm.cpio')
  temp_output = join(dir, 'rpm.contents')
  mkdir(temp_output)
    
  # sync the RPM down to the temporary directory
  sync(rpmPath, dir)
  rpmFile = join(dir, basename(rpmPath))
  
  rpm2cpio(os.open(rpmFile, os.O_RDONLY), open(filename, 'w+'))
  cpio = CpioImage(filename)
  cpio.open(point=temp_output)
  
  if not exists(output):
    mkdir(output, parent=True)

  for item in os.listdir(temp_output):
    sync(join(temp_output, item), output)

  rm(dir, recursive=True, force=True)


#------------ INTERFACES --------------------#
class InstallerInterface(EventInterface, OutputEventMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    OutputEventMixin.__init__(self)


#------------- HOOK FUNCTIONS --------------#
def preinstaller_logos_hook(interface):
  handler = InstallerLogosHandler(interface)
  addHandler(handler, 'installer_logos')
  interface.disableEvent('installer_logos')
  if interface.pre(handler) or (interface.eventForceStatus('installer_logos') or False):
    interface.enableEvent('installer_logos')
  
def installer_logos_hook(interface):
  interface.log(0, "processing installer logos")
  handler = getHandler('installer_logos')
  interface.modify(handler)

def preinstaller_release_files_hook(interface):
  handler = InstallerReleaseHandler(interface)
  addHandler(handler, 'installer_release_files')
  interface.disableEvent('installer_release_files')
  if interface.pre(handler) or (interface.eventForceStatus('installer_release_files') or False):
    interface.enableEvent('installer_release_files')

def installer_release_files_hook(interface):
  interface.log(0, "processing installer release files")  
  handler = getHandler('installer_release_files')
  interface.modify(handler)


#------------ HANDLERS -----------------#
class InstallerHandler(OutputEventHandler):
  def __init__(self, interface, data, name):
    self.interface = interface

    self.config = self.interface.config
    self.data = data

    OutputEventHandler.__init__(self, self.config, data, None,
                                mdfile=join(self.interface.getMetadata(), '%s.md' %(name,)))
    
    self.software_store = self.interface.getSoftwareStore()

  def removeObsoletes(self):
    if hasattr(self, 'output'):
      for file in self.output.keys():
        rm(file, recursive=True, force=True)

  removeInvalids = removeObsoletes

  def testInputChanged(self):
    if not self.mdvalid:
      return True
    else:
      self.configvalid = (not self._test_configvals_changed())
      self.inputvalid  = (not self._test_input_changed())
      return not(self.configvalid and self.inputvalid)
  
  def getInput(self):
    # extract the RPMs
    self.working_dir = tempfile.mkdtemp() # temporary directory, gets deleted once done    
    for rpm_name in self.data['input']:
      rpms = find(location=self.software_store, name='%s*[Rr][Pp][Mm]' %(rpm_name,))
      if len(rpms) == 0:
        raise RpmNotFoundError, "the %s RPM was not found" %(rpm_name,)
      extractRpm(rpms[0], self.working_dir)

  def addOutput(self):
    try:
      self.data['output'] = self._generate() # need to modify self.data, so that the metadata
                                             # written has all the files created.
    finally:
      rm(self.working_dir, recursive=True, force=True)

  def _generate(self): raise NotImplementedError


class InstallerLogosHandler(InstallerHandler):
  def __init__(self, interface):
    data = {
        'config': ['//installer/logos'],
        'input':  [interface.config.get('//installer/logos/package/text()',
                                        '%s-logos' %(interface.product,))],
        }
    InstallerHandler.__init__(self, interface, data, 'installer_logos')
    self.splash_lss= join(self.software_store, 'isolinux', 'splash.lss')    

  def _generate(self):
    "Create the splash.lss file and copy it to the isolinux/ folder"
    output_dir = join(self.software_store, 'isolinux')
    if not exists(output_dir):
      mkdir(output_dir, parent=True)

    # if splash.lss exists in the rpm, copy it to the isolinux/ folder
    # else convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    splash_lss = find(self.working_dir, 'splash.lss')    
    if splash_lss:
      sync(splash_lss[0], output_dir)
    else:
      splash_png = find(self.working_dir, 'syslinux-splash.png')
      if not splash_png:
        raise SplashImageNotFoundError, "no syslinux-splash.png found in logos RPM"
      splash_ppm = join(self.working_dir, 'splash.ppm')
      splash_lss = join(output_dir, 'splash.lss')
      Image.open(splash_png[0]).save(splash_ppm)
      shlib.execute('ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 < %s > %s'
                    %(splash_ppm, splash_lss,))
    pixmaps = self.createPixmaps()
    output = pixmaps + [self.splash_lss]
    return output

  def createPixmaps(self):
    """ 
    Create the product.img folder that can be used by the
    product.img module.
    """
    # delete the pixmaps folder in the images-src/product.img/ folder
    # and link the images from the RPM folder to the pixmaps folder.
    product_img = join(self.interface.getMetadata(), 'images-src', 'product.img', 'pixmaps')
    mkdir(product_img, parent=True)

    dirs_to_look = []
    for dir in ['pixmaps']:      
      dirs_to_look += find(location=self.working_dir, name=dir, type=TYPE_DIR, regex='.*anaconda.*')

    # generate the list of files to use and copy them to the product.img folder
    pixmaps = []    
    for folder in dirs_to_look:
      for image in tree(folder, prefix=True, type='f|l'):
        file_name = basename(image)
        self.interface.log(3, "hardlinking %s to %s" %(file_name, product_img,))
        pixmap = join(product_img, file_name)
        sync(image, product_img)
        pixmaps.append(pixmap)
    return pixmaps
  
  def testOutputValid(self):
    return self.interface.verifyType(self.splash_lss, FILE_TYPE_LSS)


class InstallerReleaseHandler(InstallerHandler):
  def __init__(self, interface):
    data = {
        'config': ['//installer/release-files'],
        'input':  [interface.config.get('//installer/release-files/package/text()',
                                        '%s-release' %(interface.product,))],
        }
    InstallerHandler.__init__(self, interface, data, 'installer_release_files')

  def _generate(self):
    files = {}
    rtn = []    
    for path in self.config.mget('//installer/release-files/path'):
      source = path.text
      dest = join(self.software_store, path.attrib['dest'])
      files[source] = dest
    if self.config.get('//release-files/include-in-tree/@use-default-set', 'True') in BOOLEANS_TRUE:
      for default_item in ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README', '*RPM-GPG',
                           'RPM-GPG-KEY', 'RPM-GPG-KEY-beta', 'README-BURNING-ISOS-en_US.txt',
                           'RELEASE-NOTES-en-US.html', 'stylesheet-images']:
        for item in find(location=self.working_dir, name=default_item):
          files[source] = self.software_store
    for source in files.keys():
      if isfile(source) and isdir(files[source]):
        dest = join(self.files[source], basename(source))
      rtn.append(dest)
      
    for source in files.keys():
      dest = self.files[source]
      sync(source, dest)
    return rtn

#------------- EXCEPTIONS/ERRORS ------------#
class RpmNotFoundError(Exception): pass
class SplashImageNotFoundError(StandardError): pass
