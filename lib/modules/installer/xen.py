from os.path import join

import dims.osutils as osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import InstallerInterface, FileDownloader, ImageModifier

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'xen',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['vmlinuz-xen', 'initrd-xen'],
    'parent': 'INSTALLER',
  },
]


def prexen_hook(interface):
  xen_md_struct = {
    'config':    ['/distro/main/product/text()',
                  '/distro/main/version/text()',
                  '/distro/main/fullname/text()',
                  '/distro/installer/initrd.img/path/text()'],
    'variables': ['anaconda_version'],
    'input':     [interface.config.mget('/distro/installer/initrd.img/path/text()', [])],
    'output':    [join(interface.getSoftwareStore(), 'images/xen/initrd.img'),
                  join(interface.getSoftwareStore(), 'images/xen/vmlinuz')],
  }
  
  handler = ImageModifier('initrd.img', interface, xen_md_struct, L_IMAGES,
                          mdfile=join(interface.getMetadata(), 'initrd.img-xen.md'))
  interface.add_handler('initrd.img-xen', handler)
  
  interface.disableEvent('xen')
  if interface.eventForceStatus('xen') or False:
    interface.enableEvent('xen')
  elif interface.pre(handler):
    interface.enableEvent('xen')

def xen_hook(interface):
  interface.log(0, "preparing xen images")
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  
  xen_dir = join(interface.getSoftwareStore(), 'images/xen')
  osutils.mkdir(xen_dir, parent=True)
  
  # download files
  dl = FileDownloader(L_FILES, interface)
  dl.download(d,i)
  
  # modify initrd.img
  handler = interface.get_handler('initrd.img-xen')
  interface.modify(handler)


L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="initrd.img">
        <path>images/xen</path>
      </file>
      <file id="vmlinuz">
        <path>images/xen</path>
      </file>
    </files>
  </files-entries>
</locals>
'''

L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="initrd.img">
        <format>ext2</format>
        <zipped>True</zipped>
        <path>images/xen</path>
      </image>
    </images>
    
    <!-- approx 10.2.0.3-1 - initrd.img format changed to cpio -->
    <images version="10.2.0.3-1">
      <action type="update" path="image[@id='initrd.img']">
        <format>cpio</format>
      </action>
    </images>
  </images-entries>
</locals>
'''
