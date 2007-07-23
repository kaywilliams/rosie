""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

import re
import xml.sax

from os.path  import exists, isfile, join
from urlparse import urlparse, urlunparse

from dims import filereader
from dims import listcompare
from dims import osutils
from dims import shlib
from dims import sortlib
from dims import sync
from dims import xmltree

from dims.configlib import expand_macros

from dimsbuild import difftest
from dimsbuild import locals

from dimsbuild.callback  import BuildSyncCallback
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
    ## FIXME: this is kinda restricting because only files in the
    ## input repos can be cached. URLs that point to just regular
    ## input files can't be cached.    
    dest = join(self.INPUT_STORE, repo.id, join(repo.directory, osutils.dirname(path)))
    if force:
      osutils.rm(join(self.INPUT_STORE, repo.id, join(repo.directory, path)),
                 recursive=True, force=True)
    osutils.mkdir(dest, parent=True)
    sync.sync(src, dest, *args, **kwargs)
    return join(dest, osutils.basename(path))
    
  def getBaseRepoId(self):
    "Get the id of the base repo from the config file"
    # this is kinda illegal; we need to change this to a cvar
    return self.config.get('/distro/repos/repo[@type="base"]/@id')
  
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
    # called after self.interface.config is already defined
    if self.data.has_key('input'):
      h = difftest.InputHandler(self.data['input'],
                                osutils.dirname(self.interface.config.file))
      self.DT.addHandler(h)
      self.handlers['input'] = h
    if self.data.has_key('output'):
      h = difftest.OutputHandler(self.data['output'],
                                 osutils.dirname(self.interface.config.file))
      self.DT.addHandler(h)
      self.handlers['output'] = h
    if self.data.has_key('variables'):
      h = difftest.VariablesHandler(self.data['variables'], self)
      self.DT.addHandler(h)
      self.handlers['variables'] = h
    if self.data.has_key('config'):
      h = difftest.ConfigHandler(self.data['config'], self.interface.config)
      self.DT.addHandler(h)
      self.handlers['config'] = h

  def update(self, datadict):
    for key in datadict:
      if self.handlers.has_key(key):
        self.handlers[key].update(datadict[key])
          
  def clean_metadata(self):
    self.DT.clean_metadata()
    
  def read_metadata(self):
    self.DT.read_metadata()
    
  def test_diffs(self, debug=None):
    return self.DT.changed(debug=debug)
  
  def write_metadata(self):
    self.DT.write_metadata()

class FilesMixin:
  def __init__(self, parentdir):
    self.parentdir = parentdir
    
  def add_files(self, xqueries, prefix=None, addinput=True, addoutput=True):
    "Add the input and output filelists."    
    paths = self.__read_paths(xqueries, prefix=prefix)
    if addinput:      
      self.update({
        'input': [ s for s,_ in paths ]
      })
    if addoutput:
      self.update({
        'output': [ join(d, osutils.basename(s)) for s,d in paths ]
      })

  def sync_files(self, xqueries, prefix=None):
    "Sync the input files to their output locations."
    paths = self.__read_paths(xqueries, prefix=prefix)
    for src, dst in paths:
      if not self.handlers['input'].filelists.has_key(src):
        self.handlers['input'].filelists[src] = difftest.expandPaths(src, prefix=self.handlers['input'].prefix)
      for ifile in self.handlers['input'].filelists[src]:
        if src.endswith('/'):
          fulldest = join(dst, osutils.basename(src), osutils.basename(ifile))
        else:
          fulldest = join(dst, osutils.basename(ifile))
        self.add_file(ifile, osutils.dirname(fulldest))

  def add_file(self, src, dst):
    "Add an individual file to the output location."
    if not exists(dst):
      osutils.mkdir(dst, parent=True)
    sync.sync(src, dst, callback=BuildSyncCallback(self.interface.logthresh))
    
  def remove_files(self, rmlist=[]):
    "Remove obsolete/modified files and delete empty directories."
    if not rmlist:
      # default to removing files that have been modified or
      # are no longer required.
      rmlist = self.handlers['output'].diffdict.keys()
      rmlist.extend([x \
                     for x in self.handlers['output'].oldoutput.keys() \
                     if x not in self.handlers['output'].newoutput.keys() ])
      if not rmlist:
        return
      
    rmlist.sort()
    toremove = []
    for item in rmlist:
      # remove the items in the rmlist as soon as possible, so that
      # all empty directories can be computed. Once an item is
      # deleted, its parent directories are checked to see if they are
      # empty, and if they are, they are deleted (this is what the
      # while-loop does).
      if not exists(item):
        continue
      self.interface.log(2, "removing '%s'" % item[len(self.parentdir):].lstrip('/'))
      osutils.rm(item, recursive=True, force=True)    

      item = osutils.dirname(item)        
      while not osutils.find(item, type=osutils.TYPE_FILE|osutils.TYPE_LINK):
        if item.lstrip('/') == self.parentdir.lstrip('/'):
          break
        toremove.append(item)
        item = osutils.dirname(item)

    toremove.sort()
    if toremove:
      for item in toremove:
        if exists(item):
          self.interface.log(2, "removing empty directory '%s'" % item[len(self.parentdir):].lstrip('/'))          
          osutils.rm(item, recursive=True, force=True)
    
  def __read_paths(self, xqueries, prefix=None):
    """
    Read the xpath queries specified by the xqueries parameter. For
    each of the elements found, the text node's value is the source
    and the value of the 'dest' attribute is the destination (or
    prefix if no such attribute is found).    
    """
    if type(xqueries) == str: xqueries = [xqueries]

    paths = []
    for xquery in xqueries:
      for path in self.interface.config.xpath(xquery, []):
        src = path.get('text()')
        dest = path.get('@dest', None)
        paths.append((src, dest))
    return self.__fix_paths(paths, prefix=prefix)

  def __fix_paths(self, info=[], prefix=None):
    """
    Add paths specified by the info parameter which is a list of
    tuples with the source as the first element and the destination as
    the second. If info element is not a list, it is converted to
    one.
    """
    paths = []
    
    prefix = prefix or self.parentdir
    if type(info) != list: info = [info]
    
    for item in info:
      if type(item) == str:
        src, dest = item, prefix
      else:
        assert type(item) == tuple
        src, dest = item
        if dest is None:
          dest = prefix
        else:
          if dest.startswith('/'): dest = dest[1:]
          dest = join(prefix, dest)
      paths.append((src, dest))

    return paths


#------- CLASSES ---------#
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
