from spin.locals import LocalsDict, REMOVE

__all__ = ['L_FILES']

L_FILES = LocalsDict({
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