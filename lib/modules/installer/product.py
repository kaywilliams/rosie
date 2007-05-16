from os.path import join, exists

import dims.imglib as imglib
import dims.osutils as osutils

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from lib import ImageModifier, InstallerInterface, locals_imerge

EVENTS = [
  {
    'id': 'product',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['product.img'],
    'parent': 'INSTALLER',
  },
]

HANDLERS = {}
def addHandler(handler, key): HANDLERS[key] = handler
def getHandler(key): return HANDLERS[key]

def preproduct_hook(interface):
  product_md_struct = {
    'config':    ['/distro/main/product/text()',
                  '/distro/main/version/text()',
                  '/distro/main/fullname/text()',
                  '/distro/installer/product.img/path/text()'],
    'variables': ['anaconda_version'],
    'input':     [interface.config.mget('/distro/installer/product.img/path/text()', [])],
    'output':    [join(interface.getSoftwareStore(), 'images/product.img')],
  }
  
  handler = ImageModifier('product.img', interface, product_md_struct, L_IMAGES)
  addHandler(handler, 'product.img')
  
  interface.disableEvent('product')
  if interface.eventForceStatus('product') or False:
    interface.enableEvent('product')
  elif interface.pre(handler):
    interface.enableEvent('product')

def product_hook(interface):
  interface.log(0, "generating product.img")  
  handler = getHandler('product.img')
  interface.modify(handler)


L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="product.img" virtual="True">
        <format>ext2</format>
        <path>images</path>
      </image>
    </images>
  </images-entries>
</locals>
'''
