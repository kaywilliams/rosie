from systemstudio.locals import LocalsDict, REMOVE

__all__ = ['L_CREATEREPO', 'L_CHECKSUM']

L_CREATEREPO = LocalsDict({
  "createrepo-0": {
    'xml-files': {
      'repodata/filelists.xml.gz': True,
      'repodata/other.xml.gz': True,
      'repodata/primary.xml.gz': True,
      'repodata/repomd.xml': True,
      #'repodata/comps.xml': True,
    },
    'sqlite-files': {
      'repodata/filelists.sqlite.bz2': True,
      'repodata/other.sqlite.bz2': True,
      'repodata/primary.sqlite.bz2': True,
    },
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
  "createrepo-0.9.4": { # comps.xml.gz added
    'capabilities': {
      'gzipped_groupfile': True,
    }
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
