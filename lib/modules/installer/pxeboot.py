from os.path import join, exists, islink

import os

from dims import osutils
from dims import sync

from callback import BuildSyncCallback
from event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from locals   import printf_local #!
from main     import locals_imerge

from installer.lib import FileDownloader, ImageModifier

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'pxeboot',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pxeboot'],
    'requires': ['isolinux'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'PxebootHook': 'pxeboot',
}


#------ HOOKS ------#
class PxebootHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pxeboot.pxeboot'
    
    self.interface = interface
    
    self.pxeboot_dir = join(self.interface.SOFTWARE_STORE, 'images/pxeboot')
  
  def force(self):
    osutils.rm(self.pxeboot_dir, recursive=True, force=True)
  
  def run(self):
    self.interface.log(0, "preparing pxeboot images")
    
    osutils.mkdir(self.pxeboot_dir, parent=True)
    
    for file in ['vmlinuz', 'initrd.img']:
      dest = join(self.pxeboot_dir, file)
      target = join('../../isolinux', file)
      if islink(dest):
        if os.readlink(dest) != target:
          osutils.rm(dest, force=True)
      else:
        osutils.rm(dest, force=True)
      if not exists(dest):
        os.symlink(target, dest)
  
  def apply(self):
    for file in ['vmlinuz', 'initrd.img']:
      if not exists(join(self.pxeboot_dir, file)):
        raise RuntimeError, "Unable to find '%s' in '%s'" % (file, join(self.pxeboot_dir, file))
