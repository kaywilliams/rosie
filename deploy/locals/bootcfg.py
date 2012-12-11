from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_BOOTCFG']

L_BOOTCFG = LocalsDict({
  "anaconda-0": {
    'options': {
      'method': 'method',
      'ks':     'ks',
    },
  },
  "anaconda-11.4.1.6-1": {
    'options': {
      'method': 'repo',
    }
  }
})
