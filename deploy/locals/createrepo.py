from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_CREATEREPO', 'L_CHECKSUM']

L_CREATEREPO = LocalsDict({
  "createrepo-0": {
    'capabilities': {
      'database': False,
      'update': False,
      'gzipped_groupfile': False,
    },
  },
  "createrepo-0.4.7": { # database capability added
    'capabilities': {
      'database': True,
    },
  },
  "createrepo-0.4.10": { # update capability added
    'capabilities': {
      'update': True,
    },
  },
  "createrepo-0.9.7": { # checksum option added (sha|sha256)
    'capabilities': {
      'checksum': True,
    }
  },
})
L_CHECKSUM = LocalsDict({
  "anaconda-0": {
    'type': 'sha'
   },
  "anaconda-13.21.82": {
     'type': 'sha256',
   },
})
