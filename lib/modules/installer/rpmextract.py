import os
import tempfile

from os.path            import join, exists, isdir, isfile
from rpmUtils.miscutils import rpm2cpio

from dims import shlib

from dims.imglib  import CpioImage
from dims.osutils import *
from dims.sync    import sync

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface
from main      import BOOLEANS_TRUE
from magic     import FILE_TYPE_LSS, match as magic_match
from output    import OutputEventHandler, InputInvalidError, OutputInvalidError, tree

try:
  import Image
except ImportError:
  raise ImportError("missing 'python-imaging' RPM")

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'installer-logos',
    'interface': 'EventInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['installer-logos', 'splash.lss'],
    'requires': ['software'],
    'parent': 'INSTALLER',
  },
  {
    'id': 'installer-release-files',
    'interface': 'EventInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['installer-release-files'],
    'requires': ['software'],
    'parent': 'INSTALLER',
  },  
]

HOOK_MAPPING = {
  'InstallerLogosHook':   'installer-logos',
  'InstallerReleaseHook': 'installer-release-files',
}

#------ HELPER FUNCTIONS ------#
def extractRpm(rpmPath, output=os.getcwd()):
  """ 
  Extract the contents of the RPM file specified by rpmPath to
  the output location. The rpmPath parameter can use globbing.
  
  @param rpmPath : the path to the RPM file    
  @param output  : the directory that is going to contain the RPM's
  contents
  """
  dir = tempfile.mkdtemp()
  try:
    filename = join(dir, 'rpm.cpio')
    
    # sync the RPM down to the temporary directory
    sync(rpmPath, dir)
    rpmFile = join(dir, basename(rpmPath))
    
    rpm2cpio(os.open(rpmFile, os.O_RDONLY), open(filename, 'w+'))
    cpio = CpioImage(filename)    
    if not exists(output):
      mkdir(output, parent=True)    
    cpio.open(point=output)
  finally:
    rm(dir, recursive=True, force=True)

class ExtractEventHandler(OutputEventHandler):
  def __init__(self, interface, data, mdfile):    
    self.interface = interface
    self.config = self.interface.config
    self.software_store = self.interface.SOFTWARE_STORE

    OutputEventHandler.__init__(self, self.config, data, mdfile)

  def force(self):
    self.clean_output()

  def run(self, message):
    self.modify_input_data()
    if self.check_run_status():
      self.interface.log(0, message)
      # get input - extract RPMs
      self.working_dir = tempfile.mkdtemp() # temporary directory, gets deleted once done
      for rpmname in self.data['input']:
        extractRpm(rpmname, self.working_dir)    
      # generate output files
      try:
        # need to modify self.data, so that the metadata
        # written has all the files created. Otherwise, self.data['output']
        # will be empty.
        self.data['output'] = self.generate() 
      finally:
        #rm(self.working_dir, recursive=True, force=True)
        pass
      # write metadata
      self.write_metadata()
    
  def get_rpms(self):
    return self.interface.cvars['RPMS-%s' % self.ID] or None

  def set_rpms(self, rpms):
    self.interface.cvars['RPMS-%s' % self.ID] = rpms

  def modify_input_data(self):
    rpms = self.get_rpms()
    if rpms is None:
      rpms = self.find_rpms()
      self.set_rpms(rpms)
    self.data['input'] = rpms

  def test_input_changed(self):
    if not self.mdvalid:
      return True
    else:
      self.configvalid = (not self._test_configvals_changed())
      self.inputvalid  = (not self._test_input_changed())
      self.outputvalid = (not self._test_output_changed())
      return not(self.configvalid and self.inputvalid and self.outputvalid)
    
  def _test_output_changed(self):
    # have to use this _test_output_changed() instead of OutputEventHandler's
    # because self.data['output'] hasn't been set yet. 
    if hasattr(self, 'output'):      
      for file in self.output.keys():
        if not exists(file):
          return True
        stats = os.stat(file)      
        if stats.st_size != int(self.output[file]['size']) or \
               stats.st_mtime != int(self.output[file]['mtime']):
          return True
    return False
    
  def check_run_status(self):
    if self.test_input_changed() or not self.test_output_valid():
      self.clean_output()
      return True
    return False
  
  def clean_output(self):
    if hasattr(self, 'output'):
      for file in self.output.keys():
        rm(file, recursive=True, force=True)


#------ HOOKS ------#
class InstallerLogosHook(ExtractEventHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.rpmextract.installer-logos'

    self.metadata_struct =  {
      'config': ['//installer/logos'],
      'input':  [interface.config.get('//installer/logos/package/text()',
                                     '%s-logos' %(interface.product,))],
    }
    
    ExtractEventHandler.__init__(self, interface, self.metadata_struct,
                                 join(interface.METADATA_DIR, 'installer-logos.md'))
    self.splash_lss = join(self.software_store, 'isolinux', 'splash.lss')
  
  def run(self):
    ExtractEventHandler.run(self, "processing installer logos")

  def generate(self):
    "Create the splash.lss file and copy it to the isolinux/ folder"
    output_dir = join(self.software_store, 'isolinux')
    if not exists(output_dir):
      mkdir(output_dir, parent=True)

    output = self.create_pixmaps()
    # convert the syslinux-splash.png to splash.lss and copy it
    # to the isolinux/ folder
    splash_pngs = find(self.working_dir, 'syslinux-splash.png')
    if len(splash_pngs) == 0:
      raise SplashImageNotFoundError, "no syslinux-splash.png found in logos RPM"
    shlib.execute('pngtopnm %s | ppmtolss16 \#cdcfd5=7 \#ffffff=1 \#000000=0 \#c90000=15 > %s'
                  %(splash_pngs[0], self.splash_lss,))
    output.append(self.splash_lss)
    return output

  def create_pixmaps(self):
    """ 
    Create the product.img folder that can be used by the product.img
    module.
    """
    # delete the pixmaps folder in the images-src/product.img/ folder
    # and link the images from the RPM folder to the pixmaps folder.
    product_img = join(self.interface.METADATA_DIR, 'images-src', 'product.img', 'pixmaps')
    mkdir(product_img, parent=True)

    dirs_to_look = []
    for dir in ['pixmaps']:      
      dirs_to_look.extend(find(location=self.working_dir,
                               name=dir, type=TYPE_DIR, regex='.*anaconda.*'))

    # generate the list of files to use and copy them to the product.img folder
    pixmaps = []    
    for folder in dirs_to_look:
      for image in tree(folder, prefix=True, type='f|l'):
        file_name = basename(image)
        self.interface.log(4, "hardlinking %s to %s" %(file_name, product_img,))
        pixmap = join(product_img, file_name)
        sync(image, product_img)
        pixmaps.append(pixmap)
    return pixmaps
  
  def test_output_valid(self):
    return exists(self.splash_lss) and magic_match(self.splash_lss) == FILE_TYPE_LSS
  
  def find_rpms(self):
    pkgname = self.config.get('//installer/logos/package/text()',
                              '%s-logos' %(self.interface.product,))
    rpms = find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(pkgname,),
                nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
    if len(rpms) == 0:
      rpms = find(self.interface.cvars['rpms-directory'], name='*-logos-*-*',
                  nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
      if len(rpms) == 0:
        raise RpmNotFoundError("missing logo RPM")
    return [rpms[0]]


class InstallerReleaseHook(ExtractEventHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.rpmextract.installer-release-files'

    self.metadata_struct = {
      'config': ['//installer/release-files'],
      'input':  [interface.config.get('//installer/release-files/package/text()',
                                      '%s-release' %(interface.product,))],
    }
    
    ExtractEventHandler.__init__(self, interface, self.metadata_struct,
                                 join(interface.METADATA_DIR, 'installer-release-files.md'))    
  
  def run(self):
    ExtractEventHandler.run(self, "synchronizing installer release files")

  def generate(self):
    files = {}
    rtn = []    
    for path in self.config.mget('//installer/release-files/path'):
      source = path.text
      dest = join(self.software_store, path.attrib['dest'])
      files[source] = dest
    if self.config.get('//release-files/include-in-tree/@use-default-set', 'True') in BOOLEANS_TRUE:
      for default_item in ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README',
                           '*-RPM-GPG', 'RPM-GPG-KEY-*', 'RPM-GPG-KEY-beta',
                           'README-BURNING-ISOS-en_US.txt', 'RELEASE-NOTES-en_US.html']:
        for item in find(location=self.working_dir, name=default_item):    
          files[item] = self.software_store

    for source in files.keys():
      dest = files[source]
      if isfile(source) and isdir(dest):
        dest = join(dest, basename(source))
      rtn.append(dest)      
      os.link(source, dest)
    return rtn

  def test_output_valid(self): return True

  def find_rpms(self):
    rpmnames = self.config.mget('//installer/release-files/package/text()',
                                ['%s-release' %(self.interface.product,)])
    rpms = []
    for rpmname in rpmnames:
      release_rpms = find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(rpmname,),
                          nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
      rpms.extend(release_rpms)
    if len(rpms) == 0:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        release_rpms = find(self.interface.cvars['rpms-directory'], name=glob,
                            nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]')
        rpms.extend(release_rpms)
        if len(rpms) == 0:
          raise RpmNotFoundError("missing release RPM(s)")
    return rpms    

#------ EXCEPTIONS ------#
class RpmNotFoundError(Exception): pass
class SplashImageNotFoundError(StandardError): pass
