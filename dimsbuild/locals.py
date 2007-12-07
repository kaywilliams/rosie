"""
locals.py

Locals data for dimsbuild

This file contains a number of anaconda version-specific data for various
parts of the dimsbuild process.  All information is stored in nested
LocalsDict objects.  See LocalsDict, below, for details on how it differs from
the standard dict object.
"""

from dims import sortlib

__all__ = ['DISCINFO_FORMAT_LOCALS', 'BUILDSTAMP_FORMAT_LOCALS',
           'FILES_LOCALS', 'LOGOS_LOCALS', 'INSTALLCLASS_LOCALS',
           'DEFAULT_THEME', 'RELEASE_HTML', 'GDM_GREETER_THEME',
           'LOGOS_RPM', 'THEME_XML']

class LocalsDict(dict):
  """
  A LocalsDict is a subclass of dict with a specialized key lookup system
  that aids the specific requirements of the dimsbuild locals system.

  Problem
  Certain properties of anaconda-based distributions vary depending on the
  anaconda version, such as image file location and format or discinfo file
  internal format.  While starting at a specific anaconda version, these
  particular properties may persist for a number of subsequent anaconda
  versions without changing.  In a traditional dictionary, encoding this
  would not only require a great deal of space, but would be very error prone,
  as any changes would have to potentially be applied to multiple places.

  Solution
  Instead of dictionary keys referring to a single point in anaconda's
  development cycle, a given key refers to all revisions from itself until
  the next highest key.  That is, in a LocalsDict with the keys '0', '1.5',
  and '4.0', any key request that sorts between '1.5' and '4.0' would return
  the value stored at '1.5'.  Thus, with this optimization, the developer
  need only create key, value pairs for anaconda versions where the relevant
  property in question changed in some way; all other versions can be ignored.

  LocalsDict uses sortlib for sorting of keys; as such, keys should consist
  of one or more integers separated by decimals ('.').  Sorting occurs exactly
  how one would logically expect rpm version numbers to sort (4.0 > 3.0.0,
  4.1 > 4.0.1, etc).  See sortlib.py for a full discussion of how indexes are
  sorted.

  Subsequent keys after the first provide updates to the values in previous
  keys; in the above example, then, the value returned by LocalsDict['4.0']
  would be the result of first updating LocalsDict['0'] with LocalsDict['1.5'],
  and then updating that result with LocalsDict['4.0'].  Updates are done
  recursively; that is, each level of the dictionary is updated, rather than
  just the topmost level.  In order to delete a given key, value pair, set
  a key's value to REMOVE.
  """
  def __init__(self, *args, **kwargs):
    dict.__init__(self, *args, **kwargs)
    self.setdefault('0', REMOVE)

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
    elif v is REMOVE:
      if dst.has_key(k): del(dst[k])
    else:
      dst[k] = v
  return dst

class RemoveObject: pass

REMOVE = RemoveObject()


#------ LOCALS DATA ------#
DISCINFO_FORMAT_LOCALS = LocalsDict({
  '0': {
    'timestamp': dict(index=0, string='%(timestamp)s'),
    'fullname':  dict(index=1, string='%(fullname)s'),
    'basearch':  dict(index=2, string='%(basearch)s'),
    'discs':     dict(index=3, string='%(discs)s'),
    'base':      dict(index=4, string='%(product-path)s/base'),
    'rpms':      dict(index=5, string='%(product-path)s'),
    'pixmaps':   dict(index=6, string='%(product-path)s/pixmaps'),
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
      'netstg2.img':  REMOVE,
      'hdstg2.img':   REMOVE,
      'minstg2.img':  dict(path='%(product)s/base/minstg2.img')
    },
  },
# using ext2 format as anaconda does not support cpio in all cases, i.e.
# loadUrlImages() in urlinstall.c
#  '11.1.0.11-1': { # updates.img to cpio format
#    'installer': {
#      'updates.img':  dict(format='cpio', zipped=True),
#    },
#  },
  '11.1.0.51-1': { # stage 2 images moved to images/ folder
    'stage2': {
      'stage2.img':   dict(path='images/stage2.img'),
      'minstg2.img':  dict(path='images/minstg2.img'),
    },
  },
  '11.2.0.66-1': { # removed memtest, added vesamenu.c32
    'isolinux': {
      'memtest':      REMOVE,
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
  '11.3.0.36-1': {
    'splash-image': dict(filename='syslinux-vesa-splash.jpg', format='png',
                         output='splash.jpg')
  }
})

INSTALLCLASS_LOCALS = LocalsDict({
  '0': # 11.1.0.7-1
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

  def setSteps(self, dispatch):
    BaseInstallClass.setSteps(self, dispatch);
    dispatch.skipStep("partition")

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

  def setSteps(self, dispatch):
    BaseInstallClass.setSteps(self, dispatch);
    dispatch.skipStep("partition")

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

  def setSteps(self, anaconda):
    BaseInstallClass.setSteps(self, anaconda);
    anaconda.dispatch.skipStep("partition")

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
  '0': '''<html/>\n''',
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
    'syslinux-vesa-splash.jpg': dict(
      output_format = 'png',
      output_locations = [
        '/usr/lib/anaconda-runtime/boot/syslinux-splash.png',
        '/usr/share/anaconda/pixmaps/syslinux-splash.png'
      ]
    ),
  },
  '11.2.0.66-1': {
    'syslinux-vesa-splash.jpg': dict(
      output_format = 'jpg',
      output_locations = ['/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg'],
     ),
  },
  '11.3.0.36-1': {
    'syslinux-vesa-splash.jpg': dict(
      output_format = 'png',
      output_locations = ['/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg'],
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
