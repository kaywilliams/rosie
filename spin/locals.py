"""
locals.py

Locals data for spin

This file contains a number of anaconda version-specific data for various
parts of the spin process.  All information is stored in nested
LocalsDict objects.  See LocalsDict, below, for details on how it differs from
the standard dict object.
"""

from rendition import sortlib

__all__ = ['DISCINFO_FORMAT_LOCALS', 'BUILDSTAMP_FORMAT_LOCALS',
           'FILES_LOCALS', 'LOGOS_LOCALS', 'INSTALLCLASS_LOCALS',
           'RELEASE_HTML', 'GDM_CUSTOM_THEME',
           'LOGOS_RPM_FILES_LOCALS', 'THEME_RPM_FILES_LOCALS']

class LocalsDict(dict):
  """
  A LocalsDict is a subclass of dict with a specialized key lookup system
  that aids the specific requirements of the spin locals system.

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
    'base':      dict(index=4, string='%(productpath)s/base'),
    'rpms':      dict(index=5, string='%(productpath)s'),
    'pixmaps':   dict(index=6, string='%(productpath)s/pixmaps'),
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

RELEASE_HTML = LocalsDict({
  '0': '''<html/>\n''',
})

THEME_RPM_FILES_LOCALS = LocalsDict({
  '0': {
    '/usr/share/apps/kdm/themes/Spin/background.png': dict(
      height = 1600,
      width  = 2560,
      format = 'PNG',
    ),
    '/usr/share/apps/kdm/themes/Spin/innerbackground.png': dict(
      height = 520,
      width  = 680,
      format = 'PNG',
    ),
    '/usr/share/apps/kdm/themes/Spin/screenshot.png': dict(
      height = 768,
      width  = 1024,
      format = 'PNG',
    ),
    '/usr/share/backgrounds/spin/1-spin-sunrise.png': dict(
      height = 1200,
      width  = 1920,
      format = 'PNG',
    ),
    '/usr/share/backgrounds/spin/2-spin-day.png': dict(
      height = 1200,
      width  = 1920,
      format = 'PNG',
    ),
    '/usr/share/backgrounds/spin/3-spin-sunset.png': dict(
      height = 1200,
      width  = 1920,
      format = 'PNG',
    ),
    '/usr/share/backgrounds/spin/4-spin-night.png': dict(
      height = 1200,
      width  = 1920,
      format = 'PNG',
    ),
    '/usr/share/gdm/themes/Spin/background.png': dict(
      height = 1600,
      width  = 2560,
      format = 'PNG',
    ),
    '/usr/share/gdm/themes/Spin/innerbackground.png': dict(
      height = 520,
      width  = 680,
      format = 'PNG',
    ),
    '/usr/share/gdm/themes/Spin/screenshot.png': dict(
      height = 768,
      width  = 1024,
      format = 'PNG',
    ),
    '/usr/share/gnome-screensaver/lock-dialog-system.png': dict(
      height = 314,
      width  = 400,
      format = 'PNG',
    ),
  },
})

LOGOS_RPM_FILES_LOCALS = LocalsDict({
  '0': {
    '/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg': dict(
      start_color = 'black',
      end_color = 'black',
      height = 480,
      width  = 640,
      format = 'PNG',
      output_locations = [
        '/usr/lib/anaconda-runtime/boot/syslinux-splash.png',
        '/usr/share/anaconda/pixmaps/syslinux-splash.png'
      ]
    ),
    '/usr/share/anaconda/pixmaps/anaconda_header.png': dict(
      height = 88,
      width  = 800,
      format = 'PNG',
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 18,
          font_size_min = 8,
          font_color = 'white',
          text_coords = (138, 22),
          text_max_width = 230
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (255, 52),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/progress_first-lowres.png': dict(
      height = 225,
      width  = 350,
      format = 'PNG',
      strings = [
        dict(
          text = '%(copyright)s',
          font = 'DejaVuLGCSans-ExtraLight.ttf',
          font_size = 9,
          font_color = 'white',
          text_coords = (170, 215),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/progress_first.png': dict(
      height = 325,
      width  = 500,
      format = 'PNG',
      strings = [
        dict(
          text = '%(copyright)s',
          font = 'DejaVuLGCSans-ExtraLight.ttf',
          font_size = 9,
          font_color = 'white',
          text_coords = (170, 215),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/splash.png': dict(
      height = 325,
      width  = 500,
      format = 'PNG',
      strings = [
        dict(
          text= '%(copyright)s',
          font = 'DejaVuLGCSans-ExtraLight.ttf',
          font_size = 9,
          font_color = 'white',
          text_coords = (250, 280),
        )
      ]
    ),
    '/usr/share/apps/ksplash/Themes/Spin/Preview.png': dict(
      height = 332,
      width  = 399,
      format = 'PNG',
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_active_bar.png': dict(
      height = 64,
      width  = 400,
      format = 'PNG',
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_bottom.png': dict(
      height = 19,
      width  = 400,
      format = 'PNG',
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_inactive_bar.png': dict(
      height = 64,
      width  = 400,
      format = 'PNG',
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_top.png': dict(
      height = 248,
      width  = 400,
      format = 'PNG',
    ),
    '/usr/share/firstboot/pixmaps/firstboot-left.png': dict(
      height = 600,
      width  = 160,
      format = 'PNG',
    ),
    '/usr/share/firstboot/pixmaps/splash-small.png': dict(
      height = 259,
      width  = 364,
      format = 'PNG',
    ),
    '/usr/share/pixmaps/poweredby.png': dict(
      height = 31,
      width  = 88,
      format = 'PNG',
    ),
    '/usr/share/pixmaps/splash/gnome-splash.png': dict(
      height = 293,
      width  = 420,
      format = 'PNG',
    ),
    '/usr/share/rhgb/main-logo.png': dict(
      height = 399,
      width  = 799,
      format = 'PNG',
    ),
  },
  '11.2.0.66-1': {
    '/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg': dict(
      height = 480,
      width  = 640,
      format = 'JPEG',
    )
  },
  '11.3.0.36-1': {
    '/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg': dict(
      height = 480,
      width  = 640,
      format = 'PNG',
    )
  }
})

GDM_CUSTOM_THEME = LocalsDict({
  '0': '''
# GDM Custom Configuration file.
#
# This file is the appropriate place for specifying your customizations to the
# GDM configuration.   If you run gdmsetup, it will automatically edit this
# file for you and will cause the daemon and any running GDM GUI programs to
# automatically update with the new configuration.  Not all configuration
# options are supported by gdmsetup, so to modify some values it may be
# necessary to modify this file directly by hand.
#
# This file overrides the default configuration settings.  These settings
# are stored in the GDM System Defaults configuration file, which is found
# at the following location.
#
# /usr/share/gdm/defaults.conf.
#
# This file contains comments about the meaning of each configuration option,
# so is also a useful reference.  Also refer to the documentation links at
# the end of this comment for further information.  In short, to hand-edit
# this file, simply add or modify the key=value combination in the
# appropriate section in the template below this comment section.
#
# For example, if you want to specify a different value for the Enable key
# in the "[debug]" section of your GDM System Defaults configuration file,
# then add "Enable=true" in the "[debug]" section of this file.  If the
# key already exists in this file, then simply modify it.
#
# Older versions of GDM used the "gdm.conf" file for configuration.  If your
# system has an old gdm.conf file on the system, it will be used instead of
# this file - so changes made to this file will not take effect.  Consider
# migrating your configuration to this file and removing the gdm.conf file.
#
# If you hand edit a GDM configuration file, you can run the following
# command and the GDM daemon will immediately reflect the change.  Any
# running GDM GUI programs will also be notified to update with the new
# configuration.
#
# gdmflexiserver --command="UPDATE_CONFIG <configuration key>"
#
# e.g, the "Enable" key in the "[debug]" section would be "debug/Enable".
#
# You can also run gdm-restart or gdm-safe-restart to cause GDM to restart and
# re-read the new configuration settings.  You can also restart GDM by sending
# a HUP or USR1 signal to the daemon.  HUP behaves like gdm-restart and causes
# any user session started by GDM to exit immediately while USR1 behaves like
# gdm-safe-restart and will wait until all users log out before restarting GDM.
#
# For full reference documentation see the gnome help browser under
# GNOME|System category.  You can also find the docs in HTML form on
# http://www.gnome.org/projects/gdm/
#
# NOTE: Lines that begin with "#" are considered comments.
#
# Have fun!

[daemon]

[security]

[xdmcp]

[gui]

[greeter]
GraphicalTheme=%(themename)s


[chooser]

[debug]

# Note that to disable servers defined in the GDM System Defaults
# configuration file (such as 0=Standard, you must put a line in this file
# that says 0=inactive, as described in the Configuration section of the GDM
# documentation.
#
[servers]

# Also note, that if you redefine a [server-foo] section, then GDM will
# use the definition in this file, not the GDM System Defaults configuration
# file.  It is currently not possible to disable a [server-foo] section
# defined in the GDM System Defaults configuration file.
#
'''
})
