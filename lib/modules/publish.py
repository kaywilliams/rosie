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
    'provides': ['publish'],
    'conditional-requires': ['MAIN', 'iso'],
    'parent': 'ALL',
  },
]

HOOK_MAPPING = {
  'PublishHook': 'publish',
}

class PublishInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    
    # TODO - move config location out of //main
    self.PUBLISH_STORE = join(self.config.get('//main/webroot/text()', '/var/www/html'),
                              self.config.get('//main/publishpath/text()', 'open_software'),
                              self.product)
  

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
    self.interface.log(0, "publishing output store (%s-%s)" % \
                        (self.interface.version, self.interface.release))
    
    # sync to output folder
    dest = join(self.interface.PUBLISH_STORE,
                'test/%s-%s/%s' % (self.interface.version,
                                   self.interface.release,
                                   self.interface.basearch))
    dest_os = join(dest, 'os')
    
    if not exists(dest):
      self.interface.log(2, "making directory '%s'" % dest)
    osutils.mkdir(dest_os, parent=True)
    
    sync.sync(join(self.interface.SOFTWARE_STORE, '*'),  dest_os, link=True)
    sync.sync(join(self.interface.SOFTWARE_STORE, '.*'), dest_os, link=True) # .discinfo
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % dest)
    
    # clean up old revisions
    revisions = os.listdir(join(self.interface.PUBLISH_STORE, 'test'))
    if len(revisions) > 10:
      revisions = sortlib.dsort(revisions)
      i = len(revisions) - 11 # correct for off-by-one
      while 1 >= 0:
        self.interface.log(1, "removing old revision '%s'" % revisions[i])
        osutils.rm(revisions[i], recursive=True, force=True)
        i -= 1
    
    # create published directory
    osutils.rm(join(self.interface.PUBLISH_STORE, self.interface.version), force=True)
    os.symlink('test/%s-%s' % (self.interface.version, self.interface.release),
               join(self.interface.PUBLISH_STORE, self.interface.version))
