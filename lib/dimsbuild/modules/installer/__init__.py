from os.path import join

from dims import osutils

from dimsbuild.event import EVENT_TYPE_META

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'INSTALLER',
    'properties': EVENT_TYPE_META,
  },
]

HOOK_MAPPING = {
  'InstallerHook': 'INSTALLER',
}

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

class InstallerHook:
  def __init__(self, interface):
    self.ID = 'installer.__init__'
    self.VERSION = 0
    self.interface = interface

  def pre(self):
    osutils.mkdir(join(self.interface.METADATA_DIR, 'INSTALLER'), parent=True)
