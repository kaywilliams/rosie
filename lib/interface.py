""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

import re

from urlparse import urlparse, urlunparse

from dims import filereader
from dims import listcompare
from dims import sortlib
from dims import xmltree

from dims.ConfigLib import expand_macros

import difftest
import locals


#------ INTERFACES ------#
class EventInterface:
  def __init__(self, base):
    self._base = base
    self.config = self._base.config
    self.logthresh = self._base.log.threshold
    self.errlogthresh = self._base.errlog.threshold
    
    for k,v in self._base.cvars['base-vars'].items():
      setattr(self, k, v)
    self.BASE_VARS      = self._base.cvars['base-vars']
  
    self.CACHE_DIR      = self._base.CACHE_DIR
    self.SOFTWARE_STORE = self._base.SOFTWARE_STORE
    self.INPUT_STORE    = self._base.INPUT_STORE
    self.METADATA_DIR   = self._base.METADATA_DIR
    self.TEMP_DIR       = self._base.TEMP_DIR
    
    self.cvars = self._base.cvars
    
  def expandMacros(self, text):
    return expand_macros(text, self._base.cvars['base-vars'])
  
  def cache(self, path, *args, **kwargs):
    return self._base.cachemanager.get(path, *args, **kwargs)
  
  # store information functions
  def getStoreInfo(self, i):
    """ 
    i[d],s[cheme],n[etloc],d[irectory],u[sername],p[assword] = getStoreInfo(storeid)
    
    Get information about a store
    """
    storepath = None
    try:
      storepath = '//store[@id="%s"]' % i
      self.config.get(storepath) # try to get it, if not found, fail
    except xmltree.XmlPathError, e:
      raise xmltree.XmlPathError, "The specified store, '%s', does not exist in the config file" % i
    
    s,n,d,_,_,_ = urlparse(self.config.eget(['%s/path/text()' % storepath]))
    u = self.config.eget(['%s/username/text()' % storepath], None)
    p = self.config.eget(['%s/password/text()' % storepath], None)
    
    return i, s, n, d, u, p
  
  def storeInfoJoin(self, s, n, d):
    return urlunparse((s,n,d,'','',''))
    
  def getBaseStore(self):
    "Get the id of the base store from the config file"
    return self.config.get('//stores/base/store/@id')
  
  # logging functions
  def log(self, level, msg):    self._base.log(level, msg)
  def errlog(self, level, msg): self._base.errlog(level, msg)
  
  # event processing functions
  # 'force' event functions - user specified
  def isForced(self, eventid):
    return self._base.userFC.get(eventid, None) == True
  def isSkipped(self, eventid):
    return self._base.userFC.get(eventid, None) == False
  
  # 'standard' event functions - program specified
  def enableEvent(self, eventid): self.__set_event(eventid, True)
  def disableEvent(self, eventid): self.__set_event(eventid, False)
  def isEnabled(self, eventid): return self._base.dispatch.get(eventid, err=True).enabled
  
  def __set_event(self, eventid, flag):
    self._base.dispatch.get(eventid, err=True)._set_enable_status(flag)
  
  # program control variables
  ##def set_cvar(self, flag, state):
  ##  self._base.cvars[flag] = state
  ##def get_cvar(self, flag, fallback=False):
  ##  return self._base.cvars.get(flag, fallback)
  

#------ MIXINS ------#
class ListCompareMixin:
  def __init__(self, lfn=None, rfn=None, bfn=None, cb=None):
    self.lfn = lfn
    self.rfn = rfn
    self.bfn = bfn
    self.cb  = cb
    
    self.l = None
    self.r = None
    self.b = None
  
  def compare(self, l1, l2):
    self.l, self.r, self.b = listcompare.compare(l1, l2)
    
    if len(self.b) > 0:
      if self.cb:
        self.cb.notify_both(len(self.b))
      if self.bfn:
        for i in self.b: self.bfn(i)
    if len(self.l) > 0:
      if self.cb:
        self.cb.notify_left(len(self.l))
      if self.lfn:
        for i in self.l: self.lfn(i)
    if len(self.r) > 0:
      if self.cb:
        self.cb.notify_right(len(self.r))
      if self.rfn:
        for i in self.r: self.rfn(i)

class DiffMixin:
  def __init__(self, mdfile, data):
    self.mdfile = mdfile
    self.data = data
    
    self.DT = difftest.DiffTest(self.mdfile)
    self.handlers = {} # keep a dictionary of pointers to handlers so we can access later
    
    # in order for this to run successfully, DiffMixin's __init__ function must be
    # called after self.interface and self.interface.config are already defined
    if self.data.has_key('input'):
      h = difftest.InputHandler(self.data['input'])
      self.DT.addHandler(h)
      self.handlers['input'] = h
    if self.data.has_key('output'):
      h = difftest.OutputHandler(self.data['output'])
      self.DT.addHandler(h)
      self.handlers['output'] = h
    if self.data.has_key('variables'):
      h = difftest.VariablesHandler(self.data['variables'], self.interface)
      self.DT.addHandler(h)
      self.handlers['variables'] = h
    if self.data.has_key('config'):
      h = difftest.ConfigHandler(self.data['config'], self.interface.config)
      self.DT.addHandler(h)
      self.handlers['config'] = h
    
    self.DT.read_metadata()
  
  def test_diffs(self):
    return self.DT.changed()
  
  def write_metadata(self):
    self.DT.write_metadata()
