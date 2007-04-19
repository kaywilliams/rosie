from os.path            import join, isfile
from urlgrabber.grabber import URLGrabError

import dims.filereader  as filereader
import dims.listcompare as listcompare
import dims.spider      as spider

from interface import EventInterface

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'stores',
    'provides': ['stores'],
  },
]

def stores_hook(interface):
  """Check input stores to see if their contents have changed by comparing them
  to the corresponding <store>.pkgs file in interface.getMetadata()"""
  
  interface.log(0, "generating filelists for input stores")
  changed = False
  
  for store in interface.config.mget('//stores/*/store/@id'):
    interface.log(1, store)
    n,s,d,u,p = interface.getStoreInfo(store)
    
    base = join(s,d)
    
    # get the list of .rpms in the input store
    try:
      pkgs = spider.find(base, glob='*.[Rr][Pp][Mm]', prefix=False,
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
    if len(old) > 0 or len(new) > 0:
      changed = True
      filereader.write(pkgs, oldpkgsfile)
  
  interface.setFlag('inputstore-changed', changed)

class StoreNotFoundError(StandardError): pass
