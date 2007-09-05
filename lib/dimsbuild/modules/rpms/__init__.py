from dimsbuild.event import EVENT_TYPE_META

API_VERSION = 4.1

MODULES = [
  'config',
  'default_theme',
  'localrepo',
  'logos',  
  'release',
]

EVENTS = [
  {
    'id':        'RPMS',
    'properties': EVENT_TYPE_META,
    'requires':  ['repos'],
    'conditional-requires': ['sources-enabled', 'source-repos'],
  },
]
