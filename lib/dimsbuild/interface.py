""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

import re
import xml.sax

from os.path  import join, isfile
from urlparse import urlparse, urlunparse

from dims import filereader
from dims import listcompare
from dims import osutils
from dims import shlib
from dims import sortlib
from dims import spider
from dims import sync
from dims import xmltree

from dims.configlib import expand_macros

from dimsbuild import difftest
from dimsbuild import locals

from dimsbuild.constants import BOOLEANS_TRUE

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
    self.DISTRO_DIR     = self._base.DISTRO_DIR
    self.OUTPUT_DIR     = self._base.OUTPUT_DIR
    self.SOFTWARE_STORE = self._base.SOFTWARE_STORE
    self.INPUT_STORE    = self._base.INPUT_STORE
    self.METADATA_DIR   = self._base.METADATA_DIR
    self.TEMP_DIR       = self._base.TEMP_DIR
    
    self.cvars = self._base.cvars
    
  def expandMacros(self, text):
    return expand_macros(text, self._base.cvars['base-vars'])
  
  def cache(self, repo, path, force=False, *args, **kwargs):
    src = repo.rjoin(path)
    dest = join(self.INPUT_STORE, repo.id, join(repo.directory, osutils.dirname(path)))
    if force:
      osutils.rm(join(self.INPUT_STORE, repo.id, join(repo.directory, path)),
                 recursive=True, force=True)
    osutils.mkdir(dest, parent=True)
    sync.sync(src, dest, *args, **kwargs)
    return join(dest, osutils.basename(path))
  
  def getBaseRepoId(self):
    "Get the id of the base repo from the config file"
    return self.config.get('//repos/base/repo/@id')
  
  def getAllRepos(self):
    return self.cvars['repos'].values()
  
  def getRepo(self, repoid):
    return self.cvars['repos'][repoid]

  # logging functions
  def log(self, level, msg):    self._base.log(level, msg)
  def errlog(self, level, msg): self._base.errlog(level, msg)
  
  # event processing functions
  # 'force' event functions - user specified
  def isForced(self, eventid):
    return self._base.userFC.get(eventid, None) == True or \
           self._base.autoFC.get(eventid, None) == True
  
  def isSkipped(self, eventid):
    return self._base.userFC.get(eventid, None) == False or \
           self._base.autoFC.get(eventid, None) == False
  
  # 'standard' event functions - program specified
  def enableEvent(self, eventid): self.__set_event(eventid, True)
  def disableEvent(self, eventid): self.__set_event(eventid, False)
  def isEnabled(self, eventid): return self._base.dispatch.get(eventid, err=True).enabled
  
  def __set_event(self, eventid, flag):
    self._base.dispatch.get(eventid, err=True)._set_enable_status(flag)
  
  # path-fixing functions
  def expand(self, paths=[], resolve=True, prefix=None):
    prefix = prefix or osutils.dirname(self.config.file)
    if type(paths) == str: paths = [paths]

    npaths = []
    for path in paths:
      if resolve and path.startswith('/') and path.find('://') == -1:
        path = join(prefix, path)        
      npaths.extend(self._get_files(path))

    while len(paths) > 0: paths.pop()

    for npath in npaths:
      if npath not in paths:
        paths.append(npath)
    
    return paths

  def _get_files(self, uri):
    "Return the files of a remote or local (absolute) uri"
    if uri.startswith('file:/'):
      uri = '/' + uri[6:].lstrip('/')
      
    if uri.startswith('/'): # local uri
      files = osutils.find(uri, indicators=True)
    else: # remote uri
      files = spider.find(uri)
    return files
    
      
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

  def clean_metadata(self):
    self.DT.clean_metadata()
    
  def read_metadata(self):
    self.DT.read_metadata()
    
  def test_diffs(self):
    return self.DT.changed()
  
  def write_metadata(self):
    self.DT.write_metadata()
    
  def addInput(self, input):
    """
    Add a file(s) as input.
    """
    self._add_item('input', input)

  def addOutput(self, output):
    """
    Add a file(s) as an output file.
    """
    self._add_item('output', output)

  def _add_item(self, kind, items):
    if kind not in self.handlers.keys(): return []
    if type(items) == str:
      self.handlers[kind].data.append(items)
    else:
      assert type(items) == list
      self.handlers[kind].data.extend(items)
      
  def cleanOutput(self):
    """
    Remove all files from the output files' list.
    """    
    if 'output' not in self.handlers.keys(): return         
    while len(self.handlers['output'].data) > 0:
      self.handlers['output'].data.pop()
    if len(self.handlers['output'].output) > 0:
      self.handlers['output'].output.clear()
      
  def removeOutput(self, output):
    """
    Remove a file from the list of outputs. 
    """
    if 'output' not in self.handlers.keys(): return
    if output in self.handlers['output'].data:
      self.handlers['output'].data.remove(output)
    if output in self.handlers['output'].output.keys():
      self.handlers['output'].output.pop(output)
        

class PrimaryXmlContentHandler(xml.sax.ContentHandler):
  def __init__(self):
    xml.sax.ContentHandler.__init__(self)
    
    self.locs = []
  
  def startElement(self, name, attrs):
    if name == 'location':
      self.locs.append(str(attrs.get('href')))

  
class Repo:
  def __init__(self, id):
    self.id = id
    
    self.scheme    = None
    self.netloc    = None
    self.directory = None
    self.username  = None
    self.password  = None
    
    self.remote_path = None
    self.local_path = None
    
    self.gpgcheck = False
    self.gpgkey = None
    
    self.rpms = []
    self.include = []
    self.exclude = []
    self.changed = False
    
    self.repodata_path = ''
    self.groupfile    = None
    self.primaryfile  = None
    self.filelistsfile = None
    self.otherfile    = None
    self.mdfile = 'repodata/repomd.xml'
    
    self.parser = xml.sax.make_parser()
  
  def split(self, url):
    self.scheme, self.netloc, self.directory, _, _, _ = urlparse(url)
    self.directory = self.directory.lstrip('/') # for joining convenience

  def rjoin(self, *args):
    return urlunparse((self.scheme or 'file', self.netloc, join(self.directory, *args),
                       '','',''))
  
  def ljoin(self, *args):
    return join(self.local_path, *args)
  
  def getRepoData(self, read=True):
    dest = self.ljoin(self.repodata_path, 'repodata')
    osutils.mkdir(dest, parent=True)

    sync.sync(self.rjoin(self.repodata_path, self.mdfile), dest,
              username=self.username, password=self.password)

    repomd = xmltree.read(self.ljoin(self.repodata_path, self.mdfile)).xpath('//data')
    for data in repomd:
      repofile = data.get('location/@href')
      sync.sync(self.rjoin(self.repodata_path, repofile), dest,
                username=self.username, password=self.password)
      
    if read:
      self.readRepoData(repomd)

  def readRepoData(self, repomd=None):
    repomd = repomd or xmltree.read(self.ljoin(self.repodata_path, self.mdfile)).xpath('//data')
    for data in repomd:
      repofile = data.get('location/@href')
      filetype = data.get('@type')
      if   filetype == 'group':     self.groupfile     = osutils.basename(repofile)
      elif filetype == 'primary':   self.primaryfile   = osutils.basename(repofile)
      elif filetype == 'filelists': self.filelistsfile = osutils.basename(repofile)
      elif filetype == 'other':     self.otherfile     = osutils.basename(repofile)
  
  def readRepoContents(self):
    pxmlz = self.ljoin(self.repodata_path, 'repodata', self.primaryfile)
    pxml  = join('/tmp', 'dimsbuild', '%s-primary.xml' % self.id)

    shlib.execute('gunzip -c %s > %s' % (pxmlz, pxml)) # perhaps use python for this
    
    handler = PrimaryXmlContentHandler()
    self.parser.setContentHandler(handler)
    self.parser.parse(pxml)
    osutils.rm(pxml, force=True)
    
    pkgs = handler.locs
    pkgs.sort()
    
    self.rpms = pkgs
  
  def compareRepoContents(self, oldfile):
    if isfile(oldfile):
      oldpkgs = filereader.read(oldfile)
    else:
      oldpkgs = []

    old,new,_ = listcompare.compare(oldpkgs, self.rpms)
    return old or new
  
  def writeRepoContents(self, file):
    filereader.write(self.rpms, file)


#------ FACTORY FUNCTIONS ------#
def RepoFromXml(xml):
  repo = Repo(xml.get('@id'))
  repo.remote_path   = xml.get('path/text()')
  repo.gpgcheck      = xml.get('gpgcheck/text()', 'False') in BOOLEANS_TRUE
  repo.gpgkey        = xml.get('gpgkey/text()', None)
  repo.repodata_path = xml.get('repodata-path/text()', '')
  repo.include       = xml.get('include/package/text()', [])
  repo.exclude       = xml.get('exclude/package/text()', [])
  
  repo.split(repo.remote_path)
  
  return repo
