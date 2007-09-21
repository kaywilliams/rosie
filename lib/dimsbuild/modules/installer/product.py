from dims import filereader
from dims import pps
from dims import sortlib
from dims import xmltree

from dimsbuild.event   import Event
from dimsbuild.logging import L0
from dimsbuild.misc    import locals_imerge

from dimsbuild.modules.installer.lib import ImageModifyMixin

P = pps.Path

API_VERSION = 5.0


class ProductImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'product-image',
      provides = ['product.img'],
      requires = ['anaconda-version', 'buildstamp-file', 'comps-file'],
      conditionally_comes_after = ['logos'],
    )
    
    self.DATA = {
      'config':    ['/distro/installer/product-image/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'product.img')
  
  def validate(self):
    self.validator.validate('/distro/installer/product-image', 'product.rng')
    
  def error(self, e):
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self._register_image_locals(L_IMAGES)
    self.DATA['input'].append(self.cvars['buildstamp-file'])
  
  def run(self):
    self.log(0, L0("generating product.img"))
    self.remove_output()
    self._modify()
  
  def apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))
  
  def _register_image_locals(self, locals):
    ImageModifyMixin._register_image_locals(self, locals)
    
    self.ic_locals = locals_imerge(L_INSTALLCLASSES,
                                   self.cvars['anaconda-version'])
    
    # replace element text wtih real installclass string
    indexes = sortlib.dsort(INSTALLCLASSES.keys())
    for i in indexes:
      if sortlib.dcompare(i, self.cvars['anaconda-version']) <= 0:
        self.ic_locals.get('//installclass').text = INSTALLCLASSES[i]
      else:
        break
  
  def _generate(self):
    ImageModifyMixin._generate(self)
    
    # generate installclasses if none exist
    if len((P(self.image.handler._mount)/'installclasses').findpaths(glob='*.py')) == 0:
      self._generate_installclass()
    
    # write the buildstamp file to the image
    self._write_buildstamp()
  
  def _generate_installclass(self):
    comps = xmltree.read(self.cvars['comps-file'])
    groups = comps.xpath('//group/id/text()')
    defgroups = comps.xpath('//group[default/text() = "true"]/id/text()')
    
    installclass = self.ic_locals.get('//installclass/text()')
    
    # try to perform the replacement; skip if it doesn't work
    try:
      installclass = installclass % (defgroups, groups)
    except TypeError:
      pass
    
    self.image.writeflo(filereader.writeFLO(installclass),
                        filename='custom.py', dest='installclasses')


EVENTS = {'INSTALLER': [ProductImageEvent]}

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
