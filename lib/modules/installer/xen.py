from os.path import join

import dims.osutils as osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from lib import InstallerInterface, FileDownloader, ImageModifier

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


def xen_hook(interface):
  interface.log(0, "preparing xen images")
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  
  xen_dir = join(interface.getSoftwareStore(), 'images/xen')
  osutils.mkdir(xen_dir, parent=True)
  
  # download files
  dl = FileDownloader(L_FILES, interface)
  dl.download(d,i)
  
  # modify initrd.img
  handler = ImageModifier('initrd.img', interface, INITRD_MD_STRUCT, L_IMAGES)
  if interface.pre(handler):
    interface.modify(handler)


INITRD_MD_STRUCT = {
  'config':    ['/distro/main/product/text()',
                '/distro/main/version/text()',
                '/distro/main/fullname/text()',
                '/distro/main/initrd-src/text()'],
  'variables': ['anaconda_version'],
  'input':     ['/distro/main/initrd-src/text()'],
}

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
