from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_BOOTCFG']

L_BOOTCFG = LocalsDict({
  "anaconda-0": {
    'options': {
      'method'               : 'method',
      'cdrom-requires-method': False,
      'ks'                   : 'ks',
      'ks-cdrom-path'        : 'cdrom:',
    },
  },
  "anaconda-11.4.1.6-1": {
    'options': {
      'method': 'repo',
    }
  },
  "anaconda-19.30.13": {
    'options': {
      'method'               : 'inst.repo',
      'cdrom-requires-method': True,
      'ks-path'              : 'ks=cd',
      'ks-cdrom-path'        : 'cdrom::',
    },
  },
})
