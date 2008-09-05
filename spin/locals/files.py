from rendition.magic import FILE_TYPE_EXT2FS as EXT2
from rendition.magic import FILE_TYPE_FAT    as FAT32
from rendition.magic import FILE_TYPE_CPIO   as CPIO

from spin.locals import LocalsDict, REMOVE

__all__ = ['L_FILES']

L_FILES = LocalsDict({
  "anaconda-0": {
    'isolinux': { # isolinux files
      'boot.msg':     dict(path='isolinux/boot.msg'),
      'general.msg':  dict(path='isolinux/general.msg'),
      'initrd.img':   dict(path='isolinux/initrd.img', format=EXT2, zipped=True),
      'isolinux.bin': dict(path='isolinux/isolinux.bin'),
      'isolinux.cfg': dict(path='isolinux/isolinux.cfg'),
      'memtest':      dict(path='isolinux/memtest'),
      'options.msg':  dict(path='isolinux/options.msg'),
      'param.msg':    dict(path='isolinux/param.msg'),
      'rescue.msg':   dict(path='isolinux/rescue.msg'),
      'splash.lss':   dict(path='isolinux/splash.lss'),
      'vmlinuz':      dict(path='isolinux/vmlinuz'),
    },
    'installer': { # installer images
      'product.img':  dict(path='images/product.img',  format=EXT2),
      'updates.img':  dict(path='images/updates.img',  format=EXT2),
      'diskboot.img': dict(path='images/diskboot.img', format=FAT32),
    },
    'stage2': { # stage2 images
      'stage2.img':   dict(path='%(name)s/base/stage2.img'),
      'netstg2.img':  dict(path='%(name)s/base/netstg2.img'),
      'hdstg2.img':   dict(path='%(name)s/base/hdstg2.img'),
    },
    'xen': { # xen images
      'vmlinuz-xen':  dict(path='images/xen/vmlinuz'),
      'initrd-xen':   dict(path='images/xen/initrd.img', format=EXT2, zipped=True),
    },
  },
  "anaconda-10.2.0.3-1": { # initrd images to cpio format
    'isolinux': {
      'initrd.img':   dict(format=CPIO),
    },
    'xen': {
      'initrd-xen':   dict(format=CPIO),
    },
  },
  "anaconda-10.89.1.1": { # netstg2, hdstg2 combined into minstg2
    'stage2': {
      'netstg2.img':  REMOVE,
      'hdstg2.img':   REMOVE,
      'minstg2.img':  dict(path='%(name)s/base/minstg2.img')
    },
  },
# using ext2 format as anaconda does not support cpio in all cases, i.e.
# loadUrlImages() in urlinstall.c
#  "anaconda-11.1.0.11-1": { # updates.img to cpio format
#    'installer': {
#      'updates.img':  dict(format=CPIO, zipped=True),
#    },
#  },
  "anaconda-11.1.0.51-1": { # stage 2 images moved to images/ folder
    'stage2': {
      'stage2.img':   dict(path='images/stage2.img'),
      'minstg2.img':  dict(path='images/minstg2.img'),
    },
  },
  "anaconda-11.2.0.66-1": { # removed memtest, added vesamenu.c32
    'isolinux': {
      'memtest':      REMOVE,
      'splash.lss':   REMOVE,
      'splash.jpg':   dict(path='isolinux/splash.jpg'),
      'vesamenu.c32': dict(path='isolinux/vesamenu.c32'),
    },
  },
  "anaconda-11.4.1.19-1": { # removed minstg2.img
    'stage2': {
      'minstg2.img': REMOVE,
    },
  },
#  "anaconda-11.4.1.29-1": { # renamed stage2.img to install.img
#    'stage2': {
#      'stage2.img': REMOVE,
#      'install.img': dict(path='images/install.img'),
#     },
#   },
})
