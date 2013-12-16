from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_BUILDSTAMP_FORMAT']

L_BUILDSTAMP_FORMAT = LocalsDict({
  "anaconda-0": {
    'timestamp':      dict(index=0, string='%(timestamp)s'),
    'product':        dict(index=1, string='%(fullname)s'),
    'version':        dict(index=2, string='%(version)s'),
    'productpath':    dict(index=3, string='%(packagepath)s'),
  },
  "anaconda-10.2.0.63-1": {
    'timestamp':      dict(string='%(timestamp)s.%(arch)s'),
  },
  "anaconda-10.2.1.5": {
    'bugurl':         dict(index=4, string='%(bugurl)s'),
  },
  "anaconda-11.4.0.55": {
    'productpath': REMOVE,
    'bugurl':         dict(index=3),
  },
  "anaconda-13.21.176-1": {
    'final':          dict(index=3, string='%(final)s'),
    'bugurl':         dict(index=4),
  },
  "anaconda-19.30.13": {
    'main-header':    dict(index=0, string='[Main]'),
    'product':        dict(index=1, string='Product=%(fullname)s'),
    'version':        dict(index=2, string='Version=%(version)s'),
    'bugurl':         dict(index=3, string='BugURL=%(bugurl)s'),
    'final':          dict(index=4, string='IsFinal=%(final)s'),
    'timestamp':      dict(index=5, string='UUID=%(timestamp)s.%(arch)s'),
    'compose-header': dict(index=6, string='[Compose]'),
    'composer':       dict(index=7, string='%(composer)s'),
  },
})
