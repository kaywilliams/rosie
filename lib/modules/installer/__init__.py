from event import EVENT_TYPE_META

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'INSTALLER',
    'properties': EVENT_TYPE_META,
  },
]

MODULES = [
  'bootiso',
  'discinfo',
  'diskboot',
  'installer_logos',
  'installer_release',
  'product',
  'pxeboot',
  'stage2',
  'updates',
  'xen',
]
