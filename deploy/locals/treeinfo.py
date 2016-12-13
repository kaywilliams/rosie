from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_TREEINFO_FORMAT']

L_TREEINFO_FORMAT = LocalsDict({
  "anaconda-0": {
    'general': { # general section
      'index': 0,
      'content': {
        'family':       dict(index=0, value='%(family)s'),
        'timestamp':    dict(index=1, value='%(timestamp)s'),
        'variant':      dict(index=2, value='%(family)s'),
        'totaldiscs':   dict(index=3, value='1'),
        'version':      dict(index=4, value='%(version)s'),
        'discnum':      dict(index=5, value='1'),
        'packagedir':   dict(index=6, value='%(packagepath)s'),
        'arch':         dict(index=7, value='%(arch)s'),
      },
    },
    'images-%(arch)s': { # images-%(arch)s section
      'index': 1,
      'content': {
        'kernel':       dict(index=0, value='images/pxeboot/vmlinuz'),
        'initrd':       dict(index=1, value='images/pxeboot/initrd.img'),
        'boot.iso':     dict(index=2, value='images/boot.iso'),
        'diskboot.img': dict(index=3, value='images/diskboot.img'),
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
  "anaconda-11.4.0.36": { # don't include packagedir anymore
    'general': {
      'content': {
        'packagedir':   REMOVE,
        'arch':         dict(index=6),
      },
    },
  },
  "anaconda-11.4.0.40": { # don't include diskboot.img anymore
    'images-%(arch)s': {
      'content': {
        'diskboot.img': REMOVE,
      },
    },
  },
  "anaconda-11.4.1.29-1": {
    'general': {
      'content': {
        'packagedir':   dict(index=6, value='%(packagepath)s'),
      },
    },
    'stage2': {
      'content': {
        'instimage':    REMOVE,
        'mainimage':    dict(index=0, value='images/install.img'),
      },
    },
  },
  "anaconda-19.30.13": {
    'general': {
      'content': {
        'name':         dict(index=0, value='%(fullname)s-%(version)s'),
        # 'packagedir':   dict(index=6, value=''),
      },
    },
    'stage2': {
      'content': {
        'mainimage':    dict(index=0, value='LiveOS/squashfs.img'),
      },
    },
    'images-%(arch)s': {
      'content': {
        'upgrade':      dict(index=3, value='images/pxeboot/upgrade.img'),
      },
    },
  },
  "anaconda-21.48.22.93": {
    'images-%(arch)s': {
      'content': {
        'upgrade': REMOVE,
      },
    },
  },
})

