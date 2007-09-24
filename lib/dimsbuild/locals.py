from dims import sortlib

__all__ = ['DISCINFO_FORMAT_LOCALS', 'BUILDSTAMP_FORMAT_LOCALS',
           'FILES_LOCALS', 'LOGOS_LOCALS', 'INSTALLCLASS_LOCALS',]

class LocalsDict(dict):
  def __init__(self, *args, **kwargs):
    dict.__init__(self, *args, **kwargs)
    if not self.has_key('0'):
      dict.__setitem__(self, '0', None)
    
  def __getitem__(self, key):
    ret = {}
    for index in sortlib.dsort(self.keys()):
      if sortlib.dcompare(index, key) <= 0:
        ret = rupdate(ret, dict.__getitem__(self, index))
    
    return ret
  
def rupdate(dst, src):
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

  tasks = [("Default", %s), ("Everything", %s)]

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

  tasks = [("Default", %s), ("Everything", %s)]

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
''',
})
