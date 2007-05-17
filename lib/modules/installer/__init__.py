from event import EVENT_TYPE_META

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'INSTALLER',
    'properties': EVENT_TYPE_META,
    'provides': ['INSTALLER'],
    'requires': ['.discinfo', 'software'],
  },
]

MODULES = [
  'stage2',
  'pxeboot',
  'bootiso',
  'rpmextract',
  'xen',
  'updates',
  'product',
  'diskboot',
]
