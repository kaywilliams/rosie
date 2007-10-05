from dims import sortlib

__all__ = ['DISCINFO_FORMAT_LOCALS', 'BUILDSTAMP_FORMAT_LOCALS',
           'FILES_LOCALS', 'LOGOS_LOCALS', 'INSTALLCLASS_LOCALS',
           'DEFAULT_THEME', 'RELEASE_HTML', 'GDM_GREETER_THEME',
           'LOGOS_RPM', 'THEME_XML']

class LocalsDict(dict):
  def __init__(self, *args, **kwargs):
    dict.__init__(self, *args, **kwargs)
    self.setdefault('0', None)
  
  def __getitem__(self, key):
    ret = {}
    for index in sortlib.dsort(self.keys()):
      if sortlib.dcompare(index, key) <= 0:
        ret = rupdate(ret, dict.__getitem__(self, index))
    
    return ret
  
def rupdate(dst, src):
  """ 
  Recursive dictionary updater.  Updates nested dictionaries at each level,
  rather than just at the top level.  Essentially, when calling a.update(b),
  we first check the contents of both a and b at each index i - if they are
  both dictionaries, then we call a[i].update(b[i]) instead of a[i] = b[i].
  """
  if not isinstance(src, dict):
    return src
  for k,v in src.items():
    if isinstance(v, dict):
      rdst = dst.setdefault(k, {})
      rupdate(rdst, v)
    elif v is None:
      if dst.has_key(k): del(dst[k])
    else:
      dst[k] = v
  return dst


DISCINFO_FORMAT_LOCALS = LocalsDict({
  '0': {
    'timestamp': dict(index=0, string='%(timestamp)s'),
    'fullname':  dict(index=1, string='%(fullname)s'),
    'basearch':  dict(index=2, string='%(basearch)s'),
    'discs':     dict(index=3, string='%(discs)s'),
    'base':      dict(index=4, string='%(product)s/base'),
    'rpms':      dict(index=5, string='%(product)s/RPMS'),
    'pixmaps':   dict(index=6, string='%(product)s/pixmaps'),
  },
})

BUILDSTAMP_FORMAT_LOCALS = LocalsDict({
  '0': {
    'timestamp': dict(index=0, string='%(timestamp)s'),
    'fullname':  dict(index=1, string='%(fullname)s'),
    'version':   dict(index=2, string='%(version)s'),
    'product':   dict(index=3, string='%(product)s'),
  },
  '10.2.0.63-1': {
    'timestamp': dict(string='%(timestamp)s.%(basearch)s'),
  },
  '10.2.1.5': {
    'webloc':    dict(index=4, string='%(webloc)s'),
  },
})


FILES_LOCALS = LocalsDict({
  '0': {
    'isolinux': { # isolinux files
      'boot.msg':     dict(path='isolinux/boot.msg'),
      'general.msg':  dict(path='isolinux/general.msg'),
      'initrd.img':   dict(path='isolinux/initrd.img', format='ext2', zipped=True),
      'isolinux.bin': dict(path='isolinux/isolinux.bin'),
      'isolinux.cfg': dict(path='isolinux/isolinux.cfg'),
      'memtest':      dict(path='isolinux/memtest'),
      'options.msg':  dict(path='isolinux/options.msg'),
      'param.msg':    dict(path='isolinux/param.msg'),
      'rescue.msg':   dict(path='isolinux/rescue.msg'),
      'vmlinuz':      dict(path='isolinux/vmlinuz'),
    },
    'installer': { # installer images
      'product.img':  dict(path='images/product.img',  format='ext2', virtual=True),
      'updates.img':  dict(path='images/updates.img',  format='ext2', virtual=True),
      'diskboot.img': dict(path='images/diskboot.img', format='fat32'),
    },
    'stage2': { # stage2 images
      'stage2.img':   dict(path='%(product)s/base/stage2.img'),
      'netstg2.img':  dict(path='%(product)s/base/netstg2.img'),
      'hdstg2.img':   dict(path='%(product)s/base/hdstg2.img'),
    },
    'xen': { # xen images
      'vmlinuz-xen':  dict(path='images/xen/vmlinuz'),
      'initrd-xen':   dict(path='images/xen/initrd.img', format='ext2', zipped=True),
    },
  },
  '10.2.0.3-1': { # initrd images to cpio format
    'isolinux': {
      'initrd.img':   dict(format='cpio'),
    },
    'xen': {
      'initrd-xen':   dict(format='cpio'),
    },
  },
  '10.89.1.1': { # netstg2, hdstg2 combined into minstg2
    'stage2': {
      'netstg2.img':  None,
      'hdstg2.img':   None,
      'minstg2.img':  dict(path='%(product)s/base/minstg2.img')
    },
  },
  '11.1.0.11-1': { # updates.img to cpio format
    'installer': {
      'updates.img':  dict(format='cpio', zipped=True),
    },
  },
  '11.1.0.51-1': { # stage 2 images moved to images/ folder
    'stage2': {
      'stage2.img':   dict(path='images/stage2.img'),
      'minstg2.img':  dict(path='images/minstg2.img'),
    },
  },
  '11.2.0.66-1': { # removed memtest, added vesamenu.c32
    'isolinux': {
      'memtest':      None,
      'vesamenu.c32': dict(path='isolinux/vesamenu.c32'),
    },
  },
})

LOGOS_LOCALS = LocalsDict({
  '0': {
    'splash-image': dict(filename='syslinux-splash.png', format='lss')
  },
  '11.2.0.66-1': { # no longer converts png to lss
    'splash-image': dict(filename='syslinux-vesa-splash.jpg', format='jpg')
  },
})

INSTALLCLASS_LOCALS = LocalsDict({
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
''',
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

  tasks = [("Default", %(default_groups)s), ("Everything", %(all_groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups()
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
''',
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

  tasks = [("Default", %(default_groups)s), ("Everything", %(all_groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups(anaconda)
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
''',
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

  tasks = [("Default", %(default_groups)s), ("Everything", %(all_groups)s)]

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
''',
})

DEFAULT_THEME = LocalsDict({
  '0': ''' 
chmod +w /usr/share/gdm/defaults.conf
sed -i "s/^GraphicalTheme=[a-zA-Z]*$/GraphicalTheme=%(themename)s/g" /usr/share/gdm/defaults.conf
chmod -w /usr/share/gdm/defaults.conf
'''
})

RELEASE_HTML = LocalsDict({
  '0': '''<html>
  <head>
  <style type="text/css">
  <!--
  body {
    background-color: %(bgcolor)s;
    color: %(textcolor)s;
    font-family: sans-serif;
  }
  .center {
    text-align: center;
  }
  p {
    margin-top: 20%%;
  }
  -->
  </style>
  </head>
  <body>
  <h1>
    <p class="center">Welcome to %(fullname)s!</p>
  </h1>
  </body>
</html>
'''
})

GDM_GREETER_THEME = LocalsDict({
  '0': ''' 
# This is not really a .desktop file like the rest, but it's useful to treat
# it as such
[GdmGreeterTheme]
Encoding=UTF-8
Greeter=%(product)s.xml
Name=%(fullname)s Theme
Description=%(fullname)s Theme
Author=dimsbuild
Screenshot=background.png
'''
})

LOGOS_RPM = LocalsDict({
  '0': {
    'bootloader/grub-splash.xpm.gz': dict(
      locations=['/boot/grub/splash.xpm.gz']
    ),
    'bootloader/grub-splash.png': dict(
      locations=['/boot/grub/splash.png'],
      width=640, height=480
    ),
    'anaconda/syslinux-splash.png': dict(
      locations=['/usr/lib/anaconda-runtime/boot/syslinux-splash.png'],
      width=640, height=480, textmaxwidth=600,
      textvcenter=150, texthcenter=320
    ),
    'anaconda/splashtolss.sh': dict(
      locations=['/usr/lib/anaconda-runtime/splashtolss.sh']
    ),
    'anaconda/anaconda_header.png': dict(
      locations=['/usr/share/anaconda/pixmaps/anaconda_header.png'],
      width=800, height=89, textmaxwidth=750,
      textvcenter=45, texthcenter=400
    ),
    'anaconda/progress_first-lowres.png': dict(
      locations=['/usr/share/anaconda/pixmaps/progress_first-lowres.png'],
      width=350, height=224, textmaxwidth=300,
      textvcenter=112, texthcenter=175
    ),
    'anaconda/progress_first.png': dict(
      locations=['/usr/share/anaconda/pixmaps/progress_first.png'],
      width=507, height=325, textmaxwidth=450,
      textvcenter=150, texthcenter=250
    ),
    'anaconda/splash.png': dict(
      locations=['/usr/share/anaconda/pixmaps/splash.png'],
      width=507, height=388, textmaxwidth=450,
      textvcenter=194, texthcenter=250
    ),
    'kde-splash/BlueCurve/Theme.rc': dict(
      locations=['/usr/share/apps/ksplash/Themes/BlueCurve/Theme.rc']
    ),
    'kde-splash/BlueCurve/splash_active_bar.png': dict(
      locations=['/usr/share/apps/ksplash/Themes/BlueCurve/splash_active_bar.png'],
      width=400, height=61, textmaxwidth=350,
      textvcenter=30, texthcenter=200
    ),
    'kde-splash/BlueCurve/splash_bottom.png': dict(
      locations=['/usr/share/apps/ksplash/Themes/BlueCurve/splash_bottom.png'],
      width=400, height=16, textmaxwidth=350,
      textvcenter=8, texthcenter=200
    ),
    'kde-splash/BlueCurve/splash_inactive_bar.png' : dict(
      locations=['/usr/share/apps/ksplash/Themes/BlueCurve/splash_inactive_bar.png'],
      width=400, height=61, textmaxwidth=350,
      textvcenter=30, texthcenter=200
    ),
    'kde-splash/BlueCurve/splash_top.png': dict(
      locations=['/usr/share/apps/ksplash/Themes/BlueCurve/splash_top.png'],
      width=400, height=244, textmaxwidth=350,
      textvcenter=112, texthcenter=200
    ),
    'firstboot/firstboot-header.png': dict(
      locations=['/usr/share/firstboot/pixmaps/firstboot-header.png'],
      width=800, height=58, textmaxwidth=750,
      textvcenter=25, texthcenter=400
    ),
    'firstboot/firstboot-left.png': dict(
      locations=['/usr/share/firstboot/pixmaps/firstboot-left.png'],
      width=160, height=600
    ),
    'firstboot/shadowman-round-48.png': dict(
      locations=['/usr/share/firstboot/pixmaps/shadowman-round-48.png'],
      width=48, height=48
    ),
    'firstboot/splash-small.png': dict(
      locations=['/usr/share/firstboot/pixmaps/splash-small.png'],
      width=550, height=200, textmaxwidth=530,
      textvcenter=100, texthcenter=275
    ),
    'firstboot/workstation.png': dict(
      locations=['/usr/share/firstboot/pixmaps/workstation.png'],
      width=48, height=48
    ),
    'gnome-screensaver/lock-dialog-system.glade': dict(
      locations=['/usr/share/gnome-screensaver/lock-dialog-system.glade'],
    ),
    'redhat-pixmaps/rhad.png': dict(
      locations=['/usr/share/pixmaps/redhat/rhad.png'],
      width=291, height=380
    ),
    'redhat-pixmaps/rpm.tif': dict(
      locations=['/usr/share/pixmaps/redhat/rpm.tif'],
      width=801, height=512
    ),
    'redhat-pixmaps/rpmfile-200.png': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-200.png'],
      width=200, height=200
    ),
    'redhat-pixmaps/rpmfile-32.png': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-32.png'],
      width=32, height=32
    ),
    'redhat-pixmaps/rpmfile-32.xpm': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-32.xpm'],
      width=32, height=32
    ),
    'redhat-pixmaps/rpmfile-48.png': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-48.png'],
      width=48, height=48
    ),
    'redhat-pixmaps/rpmfile-48.xpm': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-48.xpm'],
      width=48, height=48
    ),
    'redhat-pixmaps/rpmfile-64.png': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-64.png'],
      width=64, height=64
    ),
    'redhat-pixmaps/rpmfile-64.xpm': dict(
      locations=['/usr/share/pixmaps/redhat/rpmfile-64.xpm'],
      width=64, height=64
    ),
    'gnome-splash/gnome-splash.png': dict(
      locations=['/usr/share/pixmaps/splash/gnome-splash.png'],
      width=503, height=420, textmaxwidth=450,
      textvcenter=210, texthcenter=250
    ),
    'rhgb/main-file.png': dict(
      locations=['/usr/share/rhgb/main-file.png'],
      width=320, height=396, textmaxwidth=320,
      textvcenter=190, texthcenter=160
    ),
    'rhgb/system-file.png': dict(
      locations=['/usr/share/rhgb/system-file.png'],
      width=183, height=45, textmaxwidth=150,
      textvcenter=22, texthcenter=90
    ),
    'gdm/themes/%(product)s/background.png': dict(
      locations=['/usr/share/gdm/themes/%(product)s/background.png'],
      width=635, height=480
    ),
    'gdm/themes/%(product)s/GdmGreeterTheme.desktop': dict(
      locations=['/usr/share/gdm/themes/%(product)s/GdmGreeterTheme.desktop'],
    ),
    'gdm/themes/%(product)s/%(product)s.xml': dict(
      locations=['/usr/share/gdm/themes/%(product)s/%(product)s.xml'],
    ),
  },
  '11.2.0.66-1': {
    'anaconda/syslinux-vesa-splash.jpg': dict(
      locations=['/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg'],
      width=640, height=480,
      format='jpeg'
    ),
  }
})

THEME_XML = LocalsDict({
 '0': '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE greeter SYSTEM "greeter.dtd">
<greeter>
  <item type="pixmap">
    <normal file="background.png"/>
    <pos x="0" y="0" width="100%" height="-75"/>
  </item>
  
  <item type="rect">
    <normal color="#000000"/>
    <pos x="0" y="-75" width="100%" height="75"/>
    <fixed>
      <item type="rect">
        <normal color="#ffffff"/>
        <pos x="0" y="4" width="100%" height="100%"/>
        <box orientation="horizontal" spacing="10" xpadding="10" ypadding="10">
          <item type="button" id="options_button">
            <pos width="100" height="50" />
            <stock type="options"/>
          </item>
        </box>
      </item>
    </fixed>
  </item>

  <item type="label" id="clock">
    <normal color="#000000" font="Sans 12"/>
    <pos x="-160" y="-37" anchor="e"/>
    <text>%c</text>
  </item>

  <item type="rect" id="caps-lock-warning">
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="75%" width="box" height="box"/>
    <box orientation="vertical" min-width="400" xpadding="10" ypadding="5" spacing="0">
      <item type="label">
        <normal color="#000000" font="Sans 12"/>
        <pos x="50%" anchor="n"/>
	<!-- Stock label for: You've got capslock on! -->
	<stock type="caps-lock-warning"/>
      </item>
    </box>
  </item>

  <item type="rect">
    <show type="timed"/>
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="25%" width="box" height="box"/>
    <box orientation="vertical" min-width="400" xpadding="10" ypadding="5" spacing="0">
      <item type="label" id="timed-label">
        <normal color="#000000" font="Sans 12"/>
        <pos x="50%" anchor="n"/>
	<!-- Stock label for: User %s will login in %d seconds -->
	<stock type="timed-label"/>
      </item>
    </box>
  </item>

  <item type="rect">
    <normal color="#FFFFFF" alpha="0.5"/>
    <pos anchor="c" x="50%" y="50%" width="box" height="box"/>
    <box orientation="vertical" min-width="340" xpadding="30" ypadding="30" spacing="10">
      <item type="label">
        <pos anchor="n" x="50%"/>
        <normal color="#000000" font="Sans 14"/>
	<!-- Stock label for: Welcome to %h -->
	<stock type="welcome-label"/>
      </item>
      <item type="label" id="pam-prompt">
        <pos anchor="nw" x="10%"/>
        <normal color="#000000" font="Sans 12"/>
	<!-- Stock label for: Username: -->
	<stock type="username-label"/>
      </item>
      <item type="rect">
	<normal color="#000000"/>
        <pos anchor="n" x="50%" height="24" width="80%"/>
	<fixed>
	  <item type="entry" id="user-pw-entry">
            <normal color="#000000" font="Sans 12"/>
            <pos anchor="nw" x="1" y="1" height="-2" width="-2"/>
	  </item>
	</fixed>
      </item>
      <item type="button" id="ok_button">
        <pos anchor="n" x="50%" height="32" width="50%"/>
        <stock type="ok"/>
      </item>
      <item type="button" id="cancel_button">
        <pos anchor="n" x="50%" height="32" width="50%"/>
        <stock type="startagain"/>
      </item>
      <item type="label" id="pam-message">
        <pos anchor="n" x="50%"/>
        <normal color="#000000" font="Sans 12"/>
	<text></text>
      </item>
    </box>
    <fixed>
      <item type="label" id="pam-error">
        <pos anchor="n" x="50%" y="110%"/>
        <normal color="#000000" font="Sans 12"/>
        <text></text>
      </item>
    </fixed>
  </item>
</greeter>
'''
})
