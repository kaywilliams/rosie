from os.path            import join, isfile, exists
from StringIO           import StringIO
from urlgrabber.grabber import URLGrabError
from urlparse           import urlparse

import dims.filereader  as filereader
import dims.listcompare as listcompare
import dims.spider      as spider
import dims.xmltree     as xmltree

from event     import EVENT_TYPE_PROC
from interface import EventInterface
from main      import BOOLEANS_TRUE

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'stores',
    'provides': ['stores'],
    'properties': EVENT_TYPE_PROC,
    'interface': 'StoresInterface',
  },
]

class StoresInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  
  def add_store(self, xml):
    parent = self.config.get('//stores/additional')
    element = xmltree.read(StringIO(xml))
    element.parent = parent
    parent.append(element.root)
    s,n,d,_,_,_ = urlparse(element.iget('path/text()'))
    server = '://'.join((s,n))
    if server not in self._base.cachemanager.SOURCES:
      self._base.cachemanager.SOURCES.append(server)
    

def stores_hook(interface):
  """Check input stores to see if their contents have changed by comparing them
  to the corresponding <store>.pkgs file in interface.getMetadata()"""
  
  interface.log(0, "generating filelists for input stores")
  changed = False
  
  for store in interface.config.mget('//stores/*/store/@id'):
    interface.log(1, store)
    i,s,n,d,u,p = interface.getStoreInfo(store)
    
    base = interface.storeInfoJoin(s or 'file', n, d)
    
    # get the list of .rpms in the input store
    try:
      pkgs = spider.find(base, glob='*.[Rr][Pp][Mm]', nglob='repodata', prefix=False,
                         username=u, password=p)
    except URLGrabError, e:
      print e
      raise StoreNotFoundError, "The specified store '%s' at url '%s' does not appear to exist" % (store, base)
    
    oldpkgsfile = join(interface.getMetadata(), '%s.pkgs' % store)
    if isfile(oldpkgsfile):
      oldpkgs = filereader.read(oldpkgsfile)
    else:
      oldpkgs = []
    
    # test if content of input store changed
    old, new, _ = listcompare.compare(oldpkgs, pkgs)
    
    # if content changed, write new contents to file
    if len(old) > 0 or len(new) > 0 or not exists(oldpkgsfile):
      changed = True
      filereader.write(pkgs, oldpkgsfile)
    
  interface.set_cvar('inputstore-changed', changed)

class StoreNotFoundError(StandardError): pass
