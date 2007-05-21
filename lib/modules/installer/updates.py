from os.path import join, exists

import dims.imglib as imglib
import dims.osutils as osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import ImageModifier, InstallerInterface, locals_imerge

EVENTS = [
  {
    'id': 'updates',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['updates.img'],
    'requires': ['.buildstamp', 'installer-logos'],
    'parent': 'INSTALLER',
  },
]


def preupdates_hook(interface):
  updates_md_struct = {
    'config':    ['/distro/main/product/text()',
                  '/distro/main/version/text()',
                  '/distro/main/fullname/text()',
                  '/distro/installer/updates.img/path/text()'],
    'variables': ['anaconda_version'],
    'input':     [interface.config.mget('/distro/installer/updates.img/path/text()', [])],
    'output':    [join(interface.getSoftwareStore(), 'images/updates.img')],
  }
  
  handler = ImageModifier('updates.img', interface, updates_md_struct, L_IMAGES)
  interface.add_handler('updates.img', handler)
  
  interface.disableEvent('updates')
  if interface.eventForceStatus('updates') or False:
    interface.enableEvent('updates')
  elif interface.pre(handler):
    interface.enableEvent('updates')

def updates_hook(interface):
  interface.log(0, "generating updates.img")
  
  handler = interface.get_handler('updates.img')
  interface.modify(handler)


L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="updates.img" virtual="True">
        <format>ext2</format>
        <path>images</path>
      </image>
    </images>
    
    <!-- 11.1.0.11-1 updates.img format changed to cpio, zipped -->
    <images version="11.1.0.11-1">
      <action type="update" path="image[@id='updates.img']">
        <format>cpio</format>
        <zipped>True</zipped>
      </action>
    </images>
  </images-entries>
</locals>
'''
