import os

from os.path import join, exists

from dims import osutils
from dims import shlib
from dims import sortlib
from dims import sync

from event     import EVENT_TYPE_MDLR
from interface import EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'publish',
    'interface': 'PublishInterface',
    'properties': EVENT_TYPE_MDLR,
    'conditional-requires': ['MAIN', 'iso'],
    'parent': 'ALL',
  },
]

HOOK_MAPPING = {
  'PublishHook':  'publish',
}

class PublishInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)

    # TODO - move config location out of //main
    self.PUBLISH_DIR = join(self.config.get('//main/publishpath/text()', '/var/www/html/distros'),
                              self.pva)
  

#------ HOOKS ------#
class PublishHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'publish.publish'
    
    self.interface = interface
  
  def force(self):
    osutils.rm(self.interface.PUBLISH_STORE, recursive=True, force=True)
  
  def run(self):
    "Publish the contents of interface.SOFTWARE_STORE to interface.PUBLISH_STORE"
    self.interface.log(0, "publishing output store")
    
    # sync to output folder
    dest = self.interface.PUBLISH_DIR
    dest_os = join(dest, 'os')
    
    if not exists(dest):
      self.interface.log(2, "making directory '%s'" % dest)
    osutils.mkdir(dest_os, parent=True)
    
    sync.sync(join(self.interface.SOFTWARE_STORE, '*'),  dest_os, link=True)
    sync.sync(join(self.interface.SOFTWARE_STORE, '.*'), dest_os, link=True) # .discinfo
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % dest)
