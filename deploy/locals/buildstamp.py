from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_BUILDSTAMP_FORMAT']

L_BUILDSTAMP_FORMAT = LocalsDict({
  "anaconda-0": {
    'timestamp':   dict(index=0, string='%(timestamp)s'),
    'fullname':    dict(index=1, string='%(fullname)s'),
    'version':     dict(index=2, string='%(version)s'),
    'productpath': dict(index=3, string='%(packagepath)s'),
  },
  "anaconda-10.2.0.63-1": {
    'timestamp':   dict(string='%(timestamp)s.%(basearch)s'),
  },
  "anaconda-10.2.1.5": {
    'webloc':      dict(index=4, string='%(webloc)s'),
  },
  "anaconda-11.4.0.55": {
    'productpath': REMOVE,
    'webloc':      dict(index=3),
  },
   "anaconda-13.21.176-1": {
    'final':       dict(index=3, string='%(final)s'),
    'webloc':      dict(index=4),
  },
})
