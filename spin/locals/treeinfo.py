from spin.locals import LocalsDict, REMOVE

__all__ = ['L_TREEINFO_FORMAT']

L_TREEINFO_FORMAT = LocalsDict({
  '0': {
    'general': { # general section
      'index': 0,
      'content': {
        'family':       dict(index=0, value='%(product)s'),
        'timestamp':    dict(index=1, value='%(timestamp)s'),
        'variant':      dict(index=2, value='%(product)s'),
        'totaldiscs':   dict(index=3, value='1'),
        'version':      dict(index=4, value='%(version)s'),
        'discnum':      dict(index=5, value='1'),
        'packagedir':   dict(index=6, value='%(productpath)s'),
        'arch':         dict(index=7, value='%(arch)s'),
      },
    },
    'images-%(basearch)s': { # images-%(basearch)s section
      'index': 1,
      'content': {
        'kernel':       dict(index=0, value='images/pxeboot/vmlinuz'),
        'initrd':       dict(index=1, value='images/pxeboot/initrd.img'),
        'boot.iso':     dict(index=2, value='images/boot.iso'),
        'diskboot.img': dict(index=3, value='images/diskboot.img'),
      },
    },
    'images-xen': { # images-xen section
      'index': 2,
      'content': {
        'kernel':       dict(index=0, value='images/xen/vmlinuz'),
        'initrd':       dict(index=1, value='images/xen/initrd.img'),
      },
    },
    'stage2': { # stage2 section
      'index': 3,
      'content': {
        'instimage':    dict(index=0, value='images/minstg2.img'),
        'mainimage':    dict(index=1, value='images/stage2.img'),
      },
    },
  },
  '11.4.0.36': { # don't include packagedir anymore
    'general': {
      'content': {
        'packagedir':   REMOVE,
        'arch':         dict(index=6),
      },
    },
  },
  '11.4.0.40': { # don't include diskboot.img anymore
    'images-%(basearch)s': {
      'content': {
        'diskboot.img': REMOVE,
      },
    },
  },
})
