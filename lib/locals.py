""" 
locals.py

Local data/settings for dimsbuild
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "3.0"
__date__    = "March 13th, 2007"

from StringIO import StringIO

import dims.locals  as locals
import dims.sortlib as sortlib

#----------- CONSTANTS ------------#
L_BUILDSTAMP    = 'buildstamp-entries'
L_DISCINFO_PATH = 'discinfo-path-entries'
L_DISCINFO      = 'discinfo-entries'
L_FILES         = 'files-entries'
L_IMAGES        = 'images-entries'
L_INSTALLCLASS  = 'installclass-entries'

#---------- FUNCTIONS ----------#
def load(version):
  """ 
  Load locals into a Locals instance.  Performs additional processing on
  <installclass-entries> element - specifically, copies the contents of the
  LOCALS_INSTALLCLASSES dictionary at the appropriate index into this element's
  text field.  This processing is necessary because the XML parser's whitespace
  normalization removes all line breaks and tabs in the python code, making for
  an unreadable custom.py installclass.
  """
  L = locals.Locals(StringIO(LOCALS_XML), version)
  
  # postprocess installclass entries
  ic = L.getLocal(L_INSTALLCLASS)
  indexes = LOCALS_INSTALLCLASSES.keys()
  indexes = sortlib.dsort(indexes)
  for i in indexes:
    if sortlib.dcompare(i, version) <= 0:
      ic.iget('.').text = LOCALS_INSTALLCLASSES[i]
    else:
      break
  
  return L

#---------- LOCALS DATA -----------#
LOCALS_XML = \
"""<locals>
  <!-- .buildstamp format entries -->
  <buildstamp-entries>
    <buildstamp version="0">
      <line id="timestamp" position="0">
        <string-format>
          <string>%s</string>
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format>
          <string>%s</string>
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="version" position="2">
        <string-format>
          <string>%s</string>
          <format>
            <item>version</item>
          </format>
        </string-format>
      </line>
      <line id="product" position="3">
        <string-format>
          <string>%s</string>
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </buildstamp>
    <!-- 10.2.0.63-1 - added '.arch' to timestamp -->
    <buildstamp version="10.2.0.63-1">
      <action type="update" path="line[@id='timestamp']">
        <string-format>
          <string>%s.%s</string>
          <format>
            <item>timestamp</item>
            <item>arch</item>
          </format>
        </string-format>
      </action>
    </buildstamp>
    <!-- 10.2.1.5 - uncertain of actual revision number - at some point between
         10.1.0.1 and 10.2.1.5 'webloc' was added -->
    <buildstamp version="10.2.1.5">
      <action type="insert" path=".">
        <line id="webloc" position="4">
          <string-format>
            <string>%s</string>
            <format>
              <item>webloc</item>
            </format>
          </string-format>
        </line>
      </action>
    </buildstamp>
  </buildstamp-entries>
  
  <!-- .discinfo path entries -->
  <discinfo-path-entries>
    <discinfo-path version="0">
      <path>.discinfo</path>
    </discinfo-path>
  </discinfo-path-entries>
  
  <!-- .discinfo format entries -->
  <discinfo-entries>
    <discinfo version="0">
      <line id="timestamp" position="0">
        <string-format>
          <string>%s</string>
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format>
          <string>%s</string>
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="arch" position="2">
        <string-format>
          <string>%s</string>
          <format>
            <item>arch</item>
          </format>
        </string-format>
      </line>
      <line id="discs" position="3">
        <string-format>
          <string>%s</string>
          <format>
            <item>discs</item>
          </format>
        </string-format>
      </line>
      <line id="base" position="4">
        <string-format>
          <string>%s/base</string>
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
      <line id="rpms" position="5">
        <string-format>
          <string>%s/RPMS</string>
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
      <line id="pixmaps" position="6">
        <string-format>
          <string>%s/pixmaps</string>
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </discinfo>
  </discinfo-entries>
  
  <!-- file entries -->
  <files-entries>
    <files version="0">
      <!--<file id=".discinfo">
        <path>.</path>
      </file>-->
      <file id="initrd.img">
        <path>isolinux</path>
      </file>
      <file id="vmlinuz">
        <path>isolinux</path>
      </file>
      <file id="product.img" virtual="True">
        <path>
          <string-format>
            <string>%s/base</string>
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
        <virtual>True</virtual>
      </file>
      <file id="updates.img" virtual="True">
        <path>
          <string-format>
            <string>%s/base</string>
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
        <virtual>True</virtual>
      </file>
      <file id="stage2.img">
        <path>
          <string-format>
            <string>%s/base</string>
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="netstg2.img">
        <path>
          <string-format>
            <string>%s/base</string>
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="hdstg2.img">
        <path>
          <string-format>
            <string>%s/base</string>
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
    </files>
    <!-- 10.89.1-1 - netstg2.img and hdstg2.img combined into minstg2.img -->
    <files version="10.89.1-1">
      <action type="delete" path="file[@id='netstg2.img']"/>
      <action type="delete" path="file[@id='hdstg2.img']"/>
      <action type="insert" path=".">
        <file id="minstg2.img">
          <path>
            <string-format>
              <string>%s/base</string>
              <format>
                <item>product</item>
              </format>
            </string-format>
          </path>
        </file>
      </action>
    </files>
    <!-- 11.1.0.51-1 - images moved from $PROD/base/ to images/ -->
    <files version="11.1.0.51-1">
      <action type="update" path="file[@id='stage2.img']">
        <path>images</path>
      </action>
      <action type="update" path="file[@id='minstg2.img']">
        <path>images</path>
      </action>
      <action type="update" path="file[@id='product.img']">
        <path>images</path>
      </action>
      <action type="update" path="file[@id='updates.img']">
        <path>images</path>
      </action>
    </files>
  </files-entries>
  
  <!-- images entries -->
  <images-entries>
    <images version="0">
      <image id="initrd.img">
        <format>ext2</format>
        <zipped>True</zipped>
        <buildstamp>.buildstamp</buildstamp>
      </image>
      <image id="product.img">
        <format>ext2</format>
        <buildstamp>.buildstamp</buildstamp>
      </image>
      <image id="updates.img">
        <format>ext2</format>
        <buildstamp>.buildstamp</buildstamp>
      </image>
    </images>
    <!-- 10.2.0.3-1 - initrd.img from gzipped ext2 to gzipped cpio; uncertain of
         exact version number - changelogs are kinda vague -->
    <images version="10.2.0.3-1">
      <action type="update" path="image[@id='initrd.img']">
        <format>cpio</format>
      </action>
    </images>
    <!-- 11.2.0.11-1 - updates.img from ext2 to gzipped cpio -->
    <images version="11.2.0.11-1">
      <action type="update" path="image[@id='updates.img']">
        <format>cpio</format>
        <zipped>True</zipped>
      </action>
    </images>
  </images-entries>
  
  <!-- installclass entries -->
  <installclass-entries>
    <installclass version="0">0</installclass>
    <!-- 11.1.0.7-1 pass the anaconda object instead of the id -->
    <installclass version="11.1.0.7-1">
      <action type="replace" path=".">11.1.0.7-1</action>
    </installclass>
    <!-- 11.1.2.36-1 - pass anaconda object to setGroupSelection; could be before this version -->
    <installclass version="11.1.2.36-1">
      <action type="replace" path=".">11.1.2.36-1</action>
    </installclass>
  </installclass-entries>
</locals>"""

LOCALS_INSTALLCLASSES = {
# installclass data, used in locals postprocessing
  '0': 
""" 
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
"""
,
  '11.1.0.7-1':
""" 
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
"""
,
  '11.1.2.36-1':
""" 
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
"""
,
}
