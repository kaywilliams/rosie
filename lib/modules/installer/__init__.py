from event import EVENT_TYPE_META

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'INSTALLER',
    'properties': EVENT_TYPE_META,
    'provides': ['INSTALLER', 'software'],
    'requires': ['anaconda-version', 'software', 'rpms-directory'],
    'conditional-requires': ['gpgsign'], #!
  },
]

MODULES = [
  'stage2',
  'pxeboot',
  'discinfo',
  'bootiso',
  'rpmextract',
  'xen',
  'updates',
  'product',
  'diskboot',
]
