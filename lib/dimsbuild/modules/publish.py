import os

from os.path import join, exists

from dims import osutils
from dims import shlib
from dims import sortlib
from dims import sync

from dimsbuild.event     import EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface, DiffMixin

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

    self.PUBLISH_DIR = join(self.webroot, self.distrosroot, self.pva)
  

#------ HOOKS ------#
class PublishHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'publish.publish'
    
    self.interface = interface

    self.DATA =  {
      'variables': ['PUBLISH_DIR'],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'publish.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def force(self):
    osutils.rm(self.interface.PUBLISH_DIR, recursive=True, force=True)

  def run(self):
    "Publish the contents of interface.SOFTWARE_STORE to interface.PUBLISH_STORE"
    self.interface.log(0, "publishing output store")

    # Cleanup - remove old publish_dir folders
    if self.test_diffs():

      try:
        olddir = self.handlers['variables'].vars['PUBLISH_DIR']
        oldparent = os.path.dirname(olddir)

        self.interface.log(2, "removing directory '%s'" % olddir)
        osutils.rm(olddir, recursive=True, force=True)

        if not os.listdir(oldparent):
          self.interface.log(2, "removing directory '%s'" % oldparent)        
          osutils.rm(oldparent, force=True)

      except KeyError:
        pass

    if not exists(self.interface.OUTPUT_DIR): return
    
    # sync to output folder
    if not exists(self.interface.PUBLISH_DIR):
      self.interface.log(2, "making directory '%s'" % self.interface.PUBLISH_DIR)
      osutils.mkdir(self.interface.PUBLISH_DIR, parent=True)
    
    for d in ['os', 'iso', 'SRPMS']:
      src = join(self.interface.OUTPUT_DIR, d)
      if not exists(src): continue # all folders are technically optional
      sync.sync(src, self.interface.PUBLISH_DIR, link=True)
    
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % self.interface.PUBLISH_DIR)

    self.write_metadata()
