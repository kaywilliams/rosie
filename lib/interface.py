""" 
interface.py


"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "3.0"
__date__    = "March 8th, 2007"

import re

from os       import stat
from os.path  import join
from urlparse import urlparse, urlunparse

import dims.execlib    as execlib
import dims.filereader as filereader
import dims.imerge     as imerge # probably will end up in XmlTree someday
import dims.osutils    as osutils
import dims.sortlib    as sortlib
import dims.sync       as sync
import dims.xmltree    as xmltree

from dims.ConfigLib    import expand_macros
from dims.EventManager import PluginInterface

import locals

# These are going away eventually
EVENTS = {
  'release-rpm': {
    'interface': 'ReleaseRpmInterface',
    'provides': ['release.rpm'],
    'requires': [],
  },
  'logos-rpm': {
    'interface': 'LogosRpmInterface',
    'provides': ['logos.rpm'],
    'requires': [],
  },
}


#------ INTERFACES ------#
class EventInterface(PluginInterface):
  def __init__(self, base):
    self._base = base
    self.config = self._base.config
    self.logthresh = self._base.log.threshold
    self.errlogthresh = self._base.errlog.threshold
    
    self.product = self._base.base_vars['product']
    self.version = self._base.base_vars['version']
    self.release = self._base.base_vars['release']
    self.arch    = self._base.base_vars['arch']
    self.basearch = self._base.base_vars['basearch']
    self.fullname = self._base.base_vars['fullname']
    self.provider = self._base.base_vars['provider']
  
  def expandMacros(self, text):
    return expand_macros(text, self._base.base_vars)
  
  def cache(self, path, *args, **kwargs):
    self._base.cachemanager.get(path, *args, **kwargs)
  
  # store information functions
  def getStoreInfo(self, i):
    """ 
    i[d],s[cheme],n[etloc],d[irectory],u[sername],p[assword] = getStoreInfo(storeid)
    
    Get information about a store
    """
    storepath = None
    try:
      storepath = '//stores/*/store[@id="%s"]' % i
      self.config.get(storepath) # try to get it, if not found, fail
    except xmltree.XmlPathError, e:
      raise xmltree.XmlPathError, "The specified store, '%s', does not exist in the config file" % storeid
    
    s,n,d,_,_,_ = urlparse(self.config.eget(['%s/path/text()' % storepath]))
    u = self.config.eget(['%s/username/text()' % storepath])
    p = self.config.eget(['%s/password/text()' % storepath])
    
    return i, s, n, d, u, p
  
  def storeInfoJoin(self, s, n, d):
    return urlunparse((s,n,d,'','',''))
    
  def getBaseStore(self):
    "Get the id of the base store from the config file"
    return self.config.get('//stores/base/store/@id')
  
  # logging functions
  def log(self, level, msg):    self._base.log(level, msg)
  def errlog(self, level, msg): self._base.errlog(level, msg)
  
  # directory functions
  def getCache(self):         return self._base.CACHE
  def getSoftwareStore(self): return self._base.SOFTWARE_STORE
  def getMetadata(self):      return self._base.METADATA
  def getInputStore(self):    return self._base.INPUT_STORE
  def getTemp(self):          return self._base.TEMP
  
  # replacement variable functions
  def getBaseVars(self): return self._base.base_vars
  def getSourceVars(self): return self._base.source_vars
  
  # event processing functions
  # 'force' event functions - user specified
  def forceEventEnable(self, eventid, enabled):
    self.__set_event_force(eventid, enabled or None)
  def forceEventDisable(self, eventid, enabled):
    self.__set_event_force(eventid, not enabled or None)
  def eventForceStatus(self, eventid):
    if self._base.userFC.has_key(eventid):
      return self._base.userFC[eventid]
    else: return None
  
  def __set_event_force(self, eventid, flag):
    if flag is not None:
      self._base.userFC[eventid] = flag
    else:
      if self._base.userFC.has_key(eventid): del(self._base.userFC[eventid])
  
  # 'standard' event functions - program specified
  def enableEvent(self, eventid): self.__set_event(eventid, True)
  def disableEvent(self, eventid): self.__set_event(eventid, False)
  def eventStatus(self, eventid): return self._base.dispatch.get(eventid, err=True).enabled
  
  def __set_event(self, eventid, flag):
    self._base.dispatch.get(eventid, err=True)._set_enable_status(flag)
  
  # program state flags
  def setFlag(self, flag, state):
    self._base.flags[flag] = state
  def getFlag(self, flag):
    return self._base.flags.get(flag)


#------ MIXINS ------#
class FlowControlROMixin:
  def __init__(self): pass
  
  def getEventControlOption(self, eventid):
    return self._base.userFC[eventid]

class FlowControlRWMixin(FlowControlROMixin):
  def __init__(self, options):
    FlowControlROMixin.__init__(self)
    self.options = options
  
  def setEventControlOption(self, eventid, flag):
    if flag is not None:
      self._base.userFC[eventid] = flag

class VersionMixin:
  # including this mixin with an interface requires that the associated event have
  # 'stores' listed as a requirement
  def __init__(self, verfile):
    self.anaconda_version = get_anaconda_version(verfile)

class LocalsMixin:
  # including this mixin with an interface requires that the associated event have
  # 'stores' listed as a requirement
  def __init__(self, verfile, dirs):
    self.anaconda_version = get_anaconda_version(verfile)
    
    if sortlib.dcompare(self.anaconda_version, '0') < 0:
      raise ValueError, "Invalid anaconda version number '%s'" % self.anaconda_version
    
    self.locals = locals.load(self.anaconda_version)
    
    self.getLocal = self.locals.getLocal
    self.getLocalPath = self.locals.getLocalPath

class GPGMixin:
  def __init__(self):
    self.imported = False
    self.gpghomedir = join(self._base.TEMP, 'gpg')
    
    # clean up from previous runs
    osutils.rm(self.gpghomedir, recursive=True, force=True)
    osutils.mkdir(self.gpghomedir, parent=True)
    
    # import the signing gpg key
    path = self.config.get('//gpgkeys/signing-key/path/text()', None)
    if path is not None:
      sync.sync(path, self.gpghomedir)
      execlib.execute('gpg --homedir %s --import %s' % \
        (self.gpghomedir, join(self.gpghomedir, osutils.basename(path))))
      self.imported = True
  
  def sign(self, rpm): pass # to be completed when rpm signing library is done


# Old interfaces, these are going away eventually
class RpmInterface(EventInterface):
  def __init__(self):
    pass

class ReleaseRpmInterface(RpmInterface):
  def __init__(self):
    pass


#------ HELPER FUNCTIONS ------#
def get_anaconda_version(file):
  # using this function requires that the 'stores' event has run
  scan = re.compile('.*/anaconda-([\d\.]+-[\d\.]+)\..*\.[Rr][Pp][Mm]')
  version = None
  
  fl = filereader.read(file)
  for rpm in fl:
    match = scan.match(rpm)
    if match:
      try:
        version = match.groups()[0]
      except (AttributeError, IndexError), e:
        raise ValueError, "Unable to compute anaconda version from distro metadata"
      break
  if version is not None:
    return version
  else:
    raise ValueError, "Unable to compute anaconda version from distro metadata"
