from os.path  import join, exists

from dims import filereader
from dims import osutils
from dims import sortlib
from dims import xmltree

from difftest import DiffTest, OutputHandler, InputHandler, VariablesHandler, ConfigHandler
from event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from main     import locals_imerge

from installer.lib import ImageModifyMixin

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'product-image',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['product.img'],
    'requires': ['anaconda-version'],
    'conditional-requires': ['installer-logos'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'ProductHook':  'product-image',
  'ValidateHook': 'validate',
}


#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.product.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//product.img', 'product.rng')
    
class ProductHook(ImageModifyMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.product.product-image'
    
    self.interface = interface
    
    self.productimage = join(self.interface.SOFTWARE_STORE, 'images/product.img')
    
    self.DATA = {
      'config':    ['//main/product/text()',
                    '//main/version/text()',
                    '//main/fullname/text()',
                    '//installer/product.img/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [interface.config.xpath('//installer/product.img/path/text()', [])],
      'output':    [self.productimage],
    }
  
    ImageModifyMixin.__init__(self, 'product.img', interface, self.DATA)
    
  def error(self, e):
    try:
      self.close()
    except:
      pass
  
  def force(self):
    osutils.rm(self.productimage, force=True)
  
  def check(self):
    self.register_image_locals(L_IMAGES)
    
    return self.interface.isForced('product-image') or \
           not self.validate_image() or \
           self.test_diffs()
  
  def run(self):
    self.interface.log(0, "generating product.img")  
    self.modify() # see generate(), below, and ImageModifyMixin in lib.py
  
  def apply(self):
    if not exists(self.productimage):
      raise RuntimeError, "Unable to find 'product.img' at '%s'" % self.productimage
  
  def register_image_locals(self, locals):
    ImageModifyMixin.register_image_locals(self, locals)
    
    self.ic_locals = locals_imerge(L_INSTALLCLASSES,
                                   self.interface.cvars['anaconda-version'])
    
    # replace element text wtih real installclass string
    indexes = sortlib.dsort(INSTALLCLASSES.keys())
    for i in indexes:
      if sortlib.dcompare(i, self.interface.cvars['anaconda-version']) <= 0:
        self.ic_locals.get('//installclass').text = INSTALLCLASSES[i]
      else:
        break
  
  def generate(self):
    ImageModifyMixin.generate(self)
    
    # generate installclasses if none exist
    if len(osutils.find(join(self.image.mount, 'installclasses'), name='*.py')) == 0:
      self._generate_installclass()
  
  def _generate_installclass(self):
    comps = xmltree.read(join(self.interface.METADATA_DIR, 'comps.xml'))
    groups = comps.xpath('//group/id/text()')
    defgroups = comps.xpath('//group[default/text() = "true"]/id/text()')
    
    installclass = self.ic_locals.get('//installclass/text()')
    
    # try to perform the replacement; skip if it doesn't work
    try:
      installclass = installclass % (defgroups, groups)
    except TypeError:
      pass
    
    osutils.mkdir(join(self.image.mount, 'installclasses'))
    filereader.write([installclass], join(self.image.mount, 'installclasses/custom.py'))


#------ LOCALS ------#
L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="product.img" virtual="True">
        <format>ext2</format>
        <path>images</path>
      </image>
    </images>
  </images-entries>
</locals>
'''

L_INSTALLCLASSES = ''' 
<locals>
  <installclass-entries>
    <installclass version="0">0</installclass>
    
    <!-- 11.1.0.7-1 - pass anaconda object instead of id -->
    <installclass version="11.1.0.7-1">
      <action type="replace" path=".">11.1.0.7-1</action>
    </installclass>
    
    <!-- approx 11.1.2.36-1 - pass anaconda object to setGroupSelection -->
    <installclass version="11.1.2.36-1">
      <action type="replace" path=".">11.1.2.36-1</action>
    </installclass>
  </installclass-entries>
</locals>
'''

INSTALLCLASSES = {
# installclass data; used in L_INSTALLCLASS postprocessing
# can't include these directly in the xml because lxml removes whitespacing,
# which python doesn't particularly like
  '0':
'''  
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  def setInstallData(self, id):
    BaseInstallClass.setInstallData(self, id)
    BaseInstallClass.setDefaultPartitioning(self, id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, grpset, intf):
    BaseInstallClass.__init__(self, grpset)
    grpset.unselectAll()
    grpset.selectGroup('everything')

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert) 
'''
,
  '11.1.0.7-1':
''' 
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %s), ("Everything", %s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups()
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''
,
  '11.1.2.36-1':
''' 
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %s), ("Everything", %s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups(anaconda)
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''
,
  '11.2.0.66-1':
'''
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

import logging
log = logging.getLogger("anaconda")

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %s), ("Everything", %s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups(anaconda)
    log.info(grps)
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def getBackend(self, methodstr):
    if methodstr.startswith("livecd://"):
      import livecd
      return livecd.LiveCDCopyBackend
    import yuminstall
    return yuminstall.YumBackend

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''  
}
