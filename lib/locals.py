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
L_LOGOS         = 'logos-entries'


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

def printf_local(elem, vars):
  string = elem.iget('string-format/@string', elem.text)
  format = elem.get('string-format/format/item/text()', [])
  return printf(string, format, vars)

def printf(string, fmt, vars):
  for f in fmt:
    try:
      string = string.replace('%s', vars[f], 1)
    except KeyError:
      raise KeyError, "Variable '%s' not defined in supplied scope" % f
  return string

#---------- LOCALS DATA -----------#
LOCALS_XML = \
"""<locals>
  <!-- .buildstamp format entries -->
  <buildstamp-entries>
    <buildstamp version="0">
      <line id="timestamp" position="0">
        <string-format string="%s">
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format string="%s">
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="version" position="2">
        <string-format string="%s">
          <format>
            <item>version</item>
          </format>
        </string-format>
      </line>
      <line id="product" position="3">
        <string-format string="%s">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </buildstamp>
    <!-- 10.2.0.63-1 - added '.arch' to timestamp -->
    <buildstamp version="10.2.0.63-1">
      <action type="update" path="line[@id='timestamp']">
        <string-format string="%s.%s">
          <format>
            <item>timestamp</item>
            <item>basearch</item>
          </format>
        </string-format>
      </action>
    </buildstamp>
    <!-- 10.2.1.5 - uncertain of actual revision number - at some point between
         10.1.0.1 and 10.2.1.5 'webloc' was added -->
    <buildstamp version="10.2.1.5">
      <action type="insert" path=".">
        <line id="webloc" position="4">
          <string-format string="%s">
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

  <!-- logos path entries -->
  <logos-entries>
    <logos version="0">
      <logo id="bootloader/grub-splash.xpm.gz">
        <location>/boot/grub/splash.xpm.gz</location>
        <description>Background image when the grub menu is displayed. When we get around to modifying the diskboot.img so that it is a part of the output distribution, we will have to modify/create the splash.lss file.</description>
      </logo>
      <logo id="bootloader/grub-splash.png">
        <width>640</width>
        <height>480</height>
        <location>/boot/grub/splash.png</location>
        <description>Background image when the grub menu is displayed. When we get around to modifying the diskboot.img so that it is a part of the output distribution, we will have to modify/create the splash.lss file.</description>
        <textmaxwidth>600</textmaxwidth>
        <textvcenter>240</textvcenter>
        <texthcenter>320</texthcenter>
      </logo>
      <logo id="anaconda/syslinux-splash.png">
        <width>640</width>
        <height>300</height>
        <location>/usr/lib/anaconda-runtime/boot/syslinux-splash.png</location>
        <description>Used as splash image during syslinux boot, i.e. during cd/dvd, pxeand diskboot.img boot processes.</description>
        <textmaxwidth>300</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>320</texthcenter>
      </logo>
      <logo id="anaconda/splashtolss.sh">
        <location>/usr/lib/anaconda-runtime/splashtolss.sh</location>
        <description>The script that is used to convert the splash image to the lss filethat is recognized by syslinux.</description>
      </logo>
      <logo id="anaconda/anaconda_header.png">
        <width>800</width>
        <height>89</height>
        <location>/usr/share/anaconda/pixmaps/anaconda_header.png</location>
        <description>The header image displayed during the installation stage.</description>
        <textmaxwidth>750</textmaxwidth>
        <textvcenter>45</textvcenter>
        <texthcenter>400</texthcenter>
      </logo>
      <logo id="anaconda/progress_first-lowres.png">
        <width>350</width>
        <height>224</height>
        <location>/usr/share/anaconda/pixmaps/progress_first-lowres.png</location>
        <description>The image that is displayed during the install/upgrade windowsetup stage when the resolution is set to be anything but 800x600.</description>
        <textmaxwidth>300</textmaxwidth>
        <textvcenter>112</textvcenter>
        <texthcenter>175</texthcenter>        
      </logo>
      <logo id="anaconda/progress_first.png">
        <width>507</width>
        <height>325</height>
        <location>/usr/share/anaconda/pixmaps/progress_first.png</location>
        <description>The image that is displayed during the install/upgrade windowsetup stage.</description>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>150</textvcenter>
        <texthcenter>250</texthcenter>        
      </logo>
      <logo id="anaconda/splash.png">
        <width>507</width>
        <height>388</height>
        <location>/usr/share/anaconda/pixmaps/splash.png</location>
        <description>The image displayed on the welcome screen.</description>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>194</textvcenter>
        <texthcenter>250</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/Theme.rc">
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/Theme.rc</location>
        <description>The BlueCurve theme's settings.</description>
      </logo>
      <logo id="kde-splash/BlueCurve/splash_active_bar.png">
        <width>400</width>
        <height>61</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_active_bar.png</location>
        <description>The active bar icons that are displayed when the computer is booting.</description>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>30</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_bottom.png">
        <width>400</width>
        <height>16</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_bottom.png</location>
        <description>The footer for the splash image.</description>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>8</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_inactive_bar.png">
        <width>400</width>
        <height>61</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_inactive_bar.png</location>
        <description>The inactive bar icons that are displayed when the computer is booting.</description>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>30</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="kde-splash/BlueCurve/splash_top.png">
        <width>400</width>
        <height>244</height>
        <location>/usr/share/apps/ksplash/Themes/BlueCurve/splash_top.png</location>
        <description>The header for the splash image.</description>
        <textmaxwidth>350</textmaxwidth>
        <textvcenter>112</textvcenter>
        <texthcenter>200</texthcenter>        
      </logo>
      <logo id="firstboot/firstboot-header.png">
        <width>800</width>
        <height>58</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-header.png</location>
        <description>The firstboot header image.</description>
        <textmaxwidth>750</textmaxwidth>
        <textvcenter>25</textvcenter>
        <texthcenter>400</texthcenter>        
      </logo>
      <logo id="firstboot/firstboot-left.png">
        <width>160</width>
        <height>600</height>
        <location>/usr/share/firstboot/pixmaps/firstboot-left.png</location>
        <description>The image that displayed as the left bar's background image during firstboot.</description>
      </logo>
      <logo id="firstboot/shadowman-round-48.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/firstboot/pixmaps/shadowman-round-48.png</location>
        <description>The shadowman that is used during firstboot.</description>
      </logo>
      <logo id="firstboot/splash-small.png">
        <width>550</width>
        <height>200</height>
        <location>/usr/share/firstboot/pixmaps/splash-small.png</location>
        <description>The splash image displayed during firstboot.</description>
        <textmaxwidth>500</textmaxwidth>
        <textvcenter>100</textvcenter>
        <texthcenter>250</texthcenter>        
      </logo>
      <logo id="firstboot/workstation.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/firstboot/pixmaps/workstation.png</location>
        <description>The workstation image displayed during firstboot.</description>        
      </logo>
      <logo id="gnome-screensaver/lock-dialog-system.glade">
        <location>/usr/share/gnome-screensaver/lock-dialog-system.glade</location>
        <description>The glade file that designs the screensaver.</description>
      </logo>
      <logo id="redhat-pixmaps/rhad.png">
        <width>291</width>
        <height>380</height>
        <location>/usr/share/pixmaps/redhat/rhad.png</location>
        <description>RedHat Advanced Development Logo.</description>
      </logo>
      <logo id="redhat-pixmaps/rpm.tif">
        <width>801</width>
        <height>512</height>
        <location>/usr/share/pixmaps/redhat/rpm.tif</location>
        <description>The RedHat RPM logo as a .tif file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-200.png">
        <width>200</width>
        <height>200</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-200.png</location>
        <description>RPM Logo 200x200 as a png file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-32.png">
        <width>32</width>
        <height>32</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-32.png</location>
        <description>RPM logo 32x32 as a png file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-32.xpm">
        <width>32</width>
        <height>32</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-32.xpm</location>
        <description>RPM logo as a 32x32 xpm file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-48.png">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-48.png</location>
        <description>48x48 RPM logo as a png file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-48.xpm">
        <width>48</width>
        <height>48</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-48.xpm</location>
        <description>48x48 RPM logo as a xpm file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-64.png">
        <width>64</width>
        <height>64</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-64.png</location>
        <description>64x64 RPM logo as a png file.</description>
      </logo>
      <logo id="redhat-pixmaps/rpmlogo-64.xpm">
        <width>64</width>
        <height>64</height>
        <location>/usr/share/pixmaps/redhat/rpmlogo-64.xpm</location>
        <description>64x64 RPM logo as a xpm file.</description>
      </logo>
      <logo id="gnome-splash/gnome-splash.png">
        <width>503</width>
        <height>420</height>
        <location>/usr/share/pixmaps/splash/gnome-splash.png</location>
        <description>The Gnome splash image.</description>
        <textmaxwidth>450</textmaxwidth>
        <textvcenter>210</textvcenter>
        <texthcenter>250</texthcenter>        
      </logo>
      <logo id="rhgb/main-logo.png">
        <width>320</width>
        <height>396</height>
        <location>/usr/share/rhgb/main-logo.png</location>
        <description>The RedHat Graphical Boot's main logo.</description>
        <textmaxwidth>250</textmaxwidth>
        <textvcenter>198</textvcenter>
        <texthcenter>160</texthcenter>        
      </logo>
      <logo id="rhgb/system-logo.png">
        <width>183</width>
        <height>45</height>
        <location>/usr/share/rhgb/system-logo.png</location>
        <description>The RedHat Graphical Boot uses this image to display the distro name.</description>
        <textmaxwidth>120</textmaxwidth>
        <textvcenter>22</textvcenter>
        <texthcenter>90</texthcenter>        
      </logo>
      <logo id="COPYING">
        <location>/usr/share/NVR/COPYING</location>
        <description>The license information</description>
      </logo>
    </logos>
  </logos-entries>
  <!-- .discinfo format entries -->
  <discinfo-entries>
    <discinfo version="0">
      <line id="timestamp" position="0">
        <string-format string="%s">
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format string="%s">
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="basearch" position="2">
        <string-format string="%s">
          <format>
            <item>basearch</item>
          </format>
        </string-format>
      </line>
      <line id="discs" position="3">
        <string-format string="%s">
          <format>
            <item>discs</item>
          </format>
        </string-format>
      </line>
      <line id="base" position="4">
        <string-format string="%s/base">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
      <line id="rpms" position="5">
        <string-format string="%s/RPMS">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
      <line id="pixmaps" position="6">
        <string-format string="%s/pixmaps">
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
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
        <virtual>True</virtual>
      </file>
      <file id="updates.img" virtual="True">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
        <virtual>True</virtual>
      </file>
      <file id="stage2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="netstg2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="hdstg2.img">
        <path>
          <string-format string="%s/base">
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
            <string-format string="%s/base">
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
