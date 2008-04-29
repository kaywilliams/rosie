from spin.locals import LocalsDict, REMOVE

__all__ = ['L_DISCINFO_FORMAT']

L_DISCINFO_FORMAT = LocalsDict({
  "anaconda-0": {
    'timestamp': dict(index=0, string='%(timestamp)s'),
    'fullname':  dict(index=1, string='%(fullname)s'),
    'basearch':  dict(index=2, string='%(basearch)s'),
    'discs':     dict(index=3, string='%(discs)s'),
    'base':      dict(index=4, string='%(productpath)s/base'),
    'rpms':      dict(index=5, string='%(productpath)s'),
    'pixmaps':   dict(index=6, string='%(productpath)s/pixmaps'),
  },
  "anaconda-11.4.0.55": {
    'base':      REMOVE,
    'rpms':      REMOVE,
    'pixmaps':   REMOVE,
  },
})
