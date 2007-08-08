from dimsbuild.event import EVENT_TYPE_META

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'INSTALLER',
    'properties': EVENT_TYPE_META,
  },
]

MODULES = [
  'bootiso',
  'diskboot',
  'infofiles',
  'logos',
  'release',
  'isolinux',
  'product',
  'pxeboot',
  'stage2',
  'updates',
  'xen',
]
