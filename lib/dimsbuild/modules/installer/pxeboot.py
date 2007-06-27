from os.path import join, exists
import os

from dims import osutils
from dims import sync

from dimsbuild.callback import BuildSyncCallback
from dimsbuild.event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.misc     import locals_imerge

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'pxeboot-images',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pxeboot'],
    'requires': ['isolinux'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'PxebootHook': 'pxeboot-images',
}


#------ HOOKS ------#
class PxebootHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.pxeboot.pxeboot-images'
    
    self.interface = interface
    
    self.pxeboot_dir = join(self.interface.SOFTWARE_STORE, 'images/pxeboot')
  
  def force(self):
    osutils.rm(self.pxeboot_dir, recursive=True, force=True)
  
  def run(self):
    self.interface.log(0, "preparing pxeboot images")
    
    osutils.mkdir(self.pxeboot_dir, parent=True)
 
    for file in ['vmlinuz', 'initrd.img']:
      target = join(self.interface.SOFTWARE_STORE, 'isolinux', file)
      sync.sync(target, self.pxeboot_dir)
  
  def apply(self):
    for file in ['vmlinuz', 'initrd.img']:
      if not exists(join(self.pxeboot_dir, file)):
        raise RuntimeError, "Unable to find '%s' in '%s'" % (file, join(self.pxeboot_dir, file))
