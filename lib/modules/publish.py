import os

from os.path import join, exists

import dims.osutils as osutils
import dims.shlib   as shlib
import dims.sortlib as sortlib
import dims.sync    as sync

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'publish',
    'interface': 'PublishInterface',
    'properties': EVENT_TYPE_MDLR,
    'provides': ['publish'],
    'requires': ['MAIN', 'iso'],
    'parent': 'ALL',
  },
]

class PublishInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  
  def getPublishStore(self): return self._base.PUBLISH_DIR


def publish_hook(interface):
  "Publish the contents of interface.getSoftwareStore() to interface.getPublishStore()"
  
  bv = interface.getBaseVars()
  version = bv['version']
  release = bv['release']
  basearch = bv['basearch']
  interface.log(0, "publishing output store (%s-%s)" % (version, release))
  
  # sync to output folder
  dest = join(interface.getPublishStore(), 'test/%s-%s/%s' % (version, release, basearch))
  dest_os = join(dest, 'os')
  
  if not exists(dest):
    interface.log(2, "making directory '%s'" % dest)
  osutils.mkdir(dest_os, parent=True)
  
  sync.sync(join(interface.getSoftwareStore(), '*'), dest_os, link=True)
  sync.sync(join(interface.getSoftwareStore(), '.*'), dest_os, link=True) # .discinfo
  shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % dest)
  
  # clean up old revisions
  revisions = os.listdir(join(interface.getPublishStore(), 'test'))
  if len(revisions) > 10:
    revisions = sortlib.dsort(revisions)
    i = len(revisions) - 11 # correct for off-by-one
    while 1 >= 0:
      interface.log(1, "removing old revision '%s'" % revisions[i])
      osutils.rm(revisions[i], recursive=True, force=True)
      i -= 1
  
  # create published directory
  osutils.rm(join(interface.getPublishStore(), version), force=True)
  os.symlink('test/%s-%s' % (version, release),
             join(interface.getPublishStore(), version))
