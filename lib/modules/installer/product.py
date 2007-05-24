from os.path  import join, exists

import dims.filereader as filereader
import dims.imglib  as imglib
import dims.osutils as osutils
import dims.sortlib as sortlib
import dims.xmltree as xmltree

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import ImageModifier, InstallerInterface, locals_imerge

EVENTS = [
  {
    'id': 'product',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['product.img'],
    'parent': 'INSTALLER',
  },
]


def preproduct_hook(interface):
  product_md_struct = {
    'config':    ['/distro/main/product/text()',
                  '/distro/main/version/text()',
                  '/distro/main/fullname/text()',
                  '/distro/installer/product.img/path/text()'],
    'variables': ['anaconda_version'],
    'input':     [interface.config.mget('/distro/installer/product.img/path/text()', [])],
    'output':    [join(interface.getSoftwareStore(), 'images/product.img')],
  }
  
  handler = ProductImageModifier('product.img', interface, product_md_struct,
                                 L_IMAGES, L_INSTALLCLASSES)
  interface.add_handler('product.img', handler)
  
  interface.disableEvent('product')
  if interface.eventForceStatus('product') or False:
    interface.enableEvent('product')
  elif handler.pre():
    interface.enableEvent('product')

def product_hook(interface):
  interface.log(0, "generating product.img")  
  handler = interface.get_handler('product.img')
  handler.modify()


class ProductImageModifier(ImageModifier):
  def __init__(self, name, interface, data, mlocals, ic_locals):
    ImageModifier.__init__(self, name, interface, data, mlocals)
    self.ic_locals = locals_imerge(ic_locals, self.interface.anaconda_version)
    
    # replace element text with real installclass string
    indexes = sortlib.dsort(INSTALLCLASSES.keys())
    for i in indexes:
      if sortlib.dcompare(i, self.interface.anaconda_version) <= 0:
        self.ic_locals.iget('//installclass').text = INSTALLCLASSES[i]
      else:
        break
  
  def generate(self):
    ImageModifier.generate(self)
    
    # generate installclasses if none exist
    if len(osutils.find(join(self.image.mount, 'installclasses'), name='*.py')) == 0:
      self._generate_installclass()
  
  def _generate_installclass(self):
    comps = xmltree.read(join(self.interface.getMetadata(), 'comps.xml'))
    groups = comps.get('//group/id/text()')
    defgroups = comps.get('//group[default/text() = "true"]/id/text()')
    
    installclass = self.ic_locals.iget('//installclass/text()')
    
    # try to perform the replacement; skip if it doesn't work
    try:
      installclass = installclass % (defgroups, groups)
    except TypeError:
      pass
    
    osutils.mkdir(join(self.image.mount, 'installclasses'))
    filereader.write([installclass], join(self.image.mount, 'installclasses/custom.py'))

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
}
