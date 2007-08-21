""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

import csv
import os
import xml.sax

from gzip     import GzipFile
from os.path  import exists, isfile, join
from urlparse import urlparse, urlunparse
from urllib   import urlopen

from dims import filereader
from dims import listcompare
from dims import osutils
from dims import shlib
from dims import sync
from dims import xmltree

from dims.configlib import expand_macros
from dims.sync      import cache, link

from dimsbuild import difftest

from dimsbuild.callback  import BuildSyncCallback, FilesCallback
from dimsbuild.constants import BOOLEANS_TRUE

#------ INTERFACES ------#
class EventInterface:
  def __init__(self, base):
    self._base = base
    self.config = self._base.config
    self.logthresh = self._base.log.threshold
    self.errlogthresh = self._base.errlog.threshold
    
    # variables
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
    
    # sync/caching stuff
    cache_dir = self._base.mainconfig.get('/dimsbuild/cache/path/text()', None) or \
                join(self.CACHE_DIR, '.cache')
    cache_size = self._base.mainconfig.get('/dimsbuild/cache/max-size/text()', None)
    if cache_size:
      cache_size = int(cache_size)
    else:
      cache_size = self._base.CACHE_MAX_SIZE
    
    self.cache_handler  = cache.CachedSyncHandler(
                            cache_dir=cache_dir,
                            cache_max_size=cache_size,
                          )
    self.cache_callback = BuildSyncCallback(self.logthresh)
    self.copy_handler   = sync.CopyHandler()
    self.link_handler   = link.LinkHandler()

    # DiffMixin stuff
    self.handlers = {}
    self.diffset = {}

    # FilesMixin stuff
    self.files_callback = FilesCallback(self.log)
    self.syncinfo = {}
    
  def expandMacros(self, text):
    return expand_macros(text, self._base.cvars['base-vars'])
  
  def cache(self, src, dest, link=False, force=False, **kwargs):
    self.cache_handler.force = force
    if link: self.cache_handler.cache_copy_handler = self.link_handler
    else:    self.cache_handler.cache_copy_handler = self.copy_handler
    
    if not kwargs.has_key('copy_handler'):
      kwargs['copy_handler'] = self.cache_handler
    if not kwargs.has_key('callback'):
      kwargs['callback'] = self.cache_callback
    
    osutils.mkdir(dest, parent=True)
    sync.sync(src, dest, **kwargs)
    
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
    return self._base.dispatch.get(eventid, err=True).status == True
  
  def isSkipped(self, eventid):
    return self._base.dispatch.get(eventid, err=True).status == False
  
  # 'standard' event functions - program specified
  def enableEvent(self, eventid): self.__set_event(eventid, True)
  def disableEvent(self, eventid): self.__set_event(eventid, False)
  def isEnabled(self, eventid): return self._base.dispatch.get(eventid, err=True).enabled
  
  def __set_event(self, eventid, flag):
    self._base.dispatch.get(eventid, err=True)._set_enable_status(flag)

  ## DiffMixin items ##
  def setup_diff(self, mdfile, data):
    self.DT = difftest.DiffTest(mdfile)
    if data.has_key('input'):
      self.add_handler(difftest.InputHandler(data['input']))
    if data.has_key('output'):
      self.add_handler(OutputHandler(data['output']))
    if data.has_key('variables'):
      self.add_handler(difftest.VariablesHandler(data['variables'], self))
    if data.has_key('config'):
      self.add_handler(difftest.ConfigHandler(data['config'], self.config))

  def add_handler(self, handler):
    self.DT.addHandler(handler)
    self.handlers[handler.name] = handler
                 
  def clean_metadata(self):
    self.DT.clean_metadata()

  def read_metadata(self):
    self.DT.read_metadata()
    
  def test_diffs(self, debug=None):
    old_dbgval = self.DT.debug
    if debug is not None:
      self.DT.debug = debug
      
    for handler in self.handlers.values():
      if not self.diffset.has_key(handler.name):
        self.diffset[handler.name] = (len(handler.diff()) > 0)

    self.DT.debug = old_dbgval
    return (True in self.diffset.values())
  
  def has_changed(self, name, err=False):
    if not self.handlers.has_key(name):
      if err:
        raise RuntimeError("Missing %s metadata handler" % name)
      return False
    if not self.diffset.has_key(name):
      self.diffset[name] = (len(self.handlers[name].diff()) > 0)
    return self.diffset[name]
  
  def write_metadata(self):
    self.DT.write_metadata()

  ## FilesMixin stuff ##
  def remove_output(self, rmlist=None, all=False, cb=None):
    """
    remove_output([all[,cb]])

    Remove output files.
    @param all    : If all is True, remove all output files, else remove
                    the files that have changed.
    """
    if rmlist is None:
      if all:
        rmlist = self.handlers['output'].oldoutput.keys()
      else:
        rmlist = []
        # remove previously-outputted files that have been modified
        # since last run        
        if self.has_changed('output'):
          rmlist.extend([ f for f,d in self.handlers['output'].diffdict.items() if d[0] is not None ])

        # remove files the input of which has been modified
        if self.has_changed('input'):
          for ofile, ifile in self.handlers['output'].odata:
            if file not in rmlist and self.handlers['input'].diffdict.has_key(ifile):
              rmlist.append(ofile)

        # remove files that were outputted the last time, but aren't
        # needed anymore
        for oldfile in self.handlers['output'].oldoutput.keys():
          found = False
          for ds in self.syncinfo.values():
            if oldfile in ds:
              found = True
          if not found:
            rmlist.append(oldfile)
      rmlist = [ r for r in rmlist if exists(r) ]
            
    if not rmlist: return

    cb = cb or self.files_callback
    cb.remove_start()
    rmlist.sort()
    dirs = []
    # delete the files, whether or not they exist
    for rmitem in rmlist:
      cb.remove(rmitem)
      osutils.rm(rmitem, recursive=True, force=True)
      dir = osutils.dirname(rmitem)
      if dir not in dirs:
        dirs.append(dir)

    dirs = [ d for d in dirs if not osutils.find(location=d,
                                                 type=osutils.TYPE_FILE|osutils.TYPE_LINK) ]

    if not dirs: return
    dirs.reverse()
    cb.remove_dir_start()
    for dir in dirs:
      if exists(dir):
        try:
          cb.remove_dir(dir)
          os.removedirs(dir)
        except OSError:
          pass # should never happen
  
  def getFileLists(self, xpaths=[], paths=[]):
    """
    getFilesLists([xpaths[,paths]])

    Currently, getFileLists() can be called only after setup_diff() is called.
    This will get fixed once the location of the metadata file can be
    programmatically determined.
    
    @param xpaths    : [(xpath query, input prefix, output prefix), ...]
    @param paths     : [(path to file, output prefix), ...]
    """
    if not self.handlers.has_key('input'):
      self.add_handler(difftest.InputHandler([]))
    
    for x,i,o in xpaths:
      for item in self.config.xpath(x,[]):
        s = item.get('text()')
        d = item.get('@dest', '')
        if s.startswith('file://'): s = s[7:]
        if not s.startswith('/') and s.find('://') == -1:
          s = join(i,s)
        d = join(o, d.lstrip('/'))
        self.addInputFile(s,d)

    for p,o in paths:
      if type(p) != type([]):
        self.addInputFile(p,o)
      else:
        for item in p:
          self.addInputFile(item, o)

    ## TODO: filter items already in the data lists
    outputs = []
    for s,ds in self.syncinfo.items():
      for d in ds:
        outputs.append((d,s))
    return (self.syncinfo.keys(), outputs)

  def addInputFile(self, sourcefile, destdir):
    inputs = self.handlers['input'].mdadd(sourcefile)

    if type(sourcefile) == type(()):
      sourcefile = sourcefile[0]
          
    if sourcefile.startswith('file://'):
      sourcefile = sourcefile[7:]
      
    if not inputs:
      if sourcefile.find('://') == -1:
        if not exists(sourcefile):
          raise IOError("missing input file(s) %s" % sourcefile)
      else:
        try:
          site = urlopen(sourcefile)
        except:
          raise IOError("missing input file(s) %s" % sourcefile)
        else:
          site.close()

    for f in inputs:
      if not self.syncinfo.has_key(f):
        self.syncinfo[f] = []
      ofile = join(destdir, f[sourcefile.rstrip('/').rfind('/')+1:])
      self.syncinfo[f].append(ofile)

  def list_output(self, source):
    """
    list_output(source)
    
    Returns the list of output files corresponding to an input file/directory.

    @param source: the source file for which the output files' list is
                   requested.    
    """
    return [ d for d,s in self.handlers['output'].odata if s is not None and s.startswith(source) ]
    
  def sync_input(self, action=None, cb=None):
    """
    sync_input([action[,cb]])
    
    Sync the input files to their output locations.
    
    @param action: the function to call with the source file and
                   destination as parameters. If None, simply sync the
                   source file to the destination.
    """
    sync_items = []
    for s in self.syncinfo.keys():      
      sync_items.extend( [ (s,d) for d in self.syncinfo[s] if not exists(d) ] )    

    # return if there is nothing to sync
    if not sync_items: return
    cb = cb or self.files_callback
    cb.sync_file_start()
    
    sync_items.sort(lambda x,y: cmp(x[1], y[1]))
    for s,d in sync_items:
      cb.sync_file(s,d)
      if action: action(s, osutils.dirname(d))
      else:      self.cache(s, osutils.dirname(d))
      
    return [ d for _,d in sync_items ]

#------- DIFFTEST HANDLERS -----#
class OutputHandler:
  def __init__(self, data):
    self.name  = 'output'
    self.odata = data
    self.oldoutput = {}
    self.diffdict = {}

    self.refresh()
    
  def refresh(self):
    torem = []
    toapp = []

    for datum in self.odata:
      if type(datum) == type(''):
        torem.append(datum)
        toapp.append((datum, None))
      elif type(datum) == type([]):
        torem.append(datum)
        toapp.extend([ (x,None) for x in datum ])
      
    for rem in torem: self.odata.remove(rem)
    for app in toapp: self.odata.append(app)

  def clear(self):
    self.oldoutput.clear()

  def mdread(self, metadata):
    for file in metadata.xpath('/metadata/output/file'):
      self.oldoutput[file.get('@path')] = (int(file.get('size/text()')),
                                           int(file.get('mtime/text()')),
                                           file.get('source/text()', None))
      
  def mdwrite(self, root):
    self.refresh()        
    try: root.remove(root.get('output'))
    except TypeError: pass
    
    parent = xmltree.uElement('output', parent=root)
    for file, source in self.odata:
      info = difftest.expandPaths(file)
      for o,s,m in info:
        e = xmltree.Element('file', parent=parent, attrs={'path': o})
        xmltree.Element('size', parent=e, text=str(s))
        xmltree.Element('mtime', parent=e, text=str(m))
        if source:
          xmltree.Element('source', parent=e, text=source)

  def diff(self):
    self.refresh()
    newitems = {}
    for file in self.oldoutput.keys():
      size, mtime = difftest.DiffTuple(file)
      newitems[file] = (size, mtime, self.oldoutput[file][2])
    self.diffdict = difftest.diff(self.oldoutput, newitems)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict

#------- CLASSES ---------#
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
    
    self.repoinfo = []
    
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
  
  def getRepoData(self):
    dest = self.ljoin(self.repodata_path, 'repodata')
    osutils.mkdir(dest, parent=True)

    sync.sync(self.rjoin(self.repodata_path, self.mdfile), dest,
              username=self.username, password=self.password)

    repomd = xmltree.read(self.ljoin(self.repodata_path, self.mdfile)).xpath('//data')
    for data in repomd:
      repofile = data.get('location/@href')
      sync.sync(self.rjoin(self.repodata_path, repofile), dest,
                username=self.username, password=self.password)

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
  
  def readRepoContents(self, repofile=None):
    if repofile is None:
      self.repoinfo = []
      pxml = GzipFile(filename=self.ljoin(self.repodata_path, 'repodata', self.primaryfile),
                      mode='rt')
      tree = xmltree.read(pxml)
      pxml.close()      
      for package in tree.xpath('/metadata/package', []):
        location = package.get('location/@href')
        size     = package.get('size/@package')
        mtime    = package.get('time/@file')
        self.repoinfo.append({
          'file':  self.rjoin(self.repodata_path, location),
          'size':  int(size),
          'mtime': int(mtime),
        })
    else:
      self.repoinfo = []      
      mr = open(repofile, 'r')
      mreader = csv.DictReader(mr, ['file', 'size', 'mtime'], lineterminator='\n')
      for item in mreader:
        self.repoinfo.append({
          'mtime': int(item['mtime']),
          'size':  int(item['size']),
          'file':  item['file'],
        })      
      mr.close()      

  def compareRepoContents(self, oldfile, what=None):
    "@param what: the item to compare. Can be any of 'mtime', 'size', or 'file'."
    oldpkgs = []
    newpkgs = self.repoinfo

    if isfile(oldfile):
      mr = open(oldfile, 'r')
      mreader = csv.DictReader(mr, ['file', 'size', 'mtime'], lineterminator='\n')
      for item in mreader:
        oldpkgs.append({
          'mtime': int(item['mtime']),
          'size':  int(item['size']),
          'file':  item['file'],
        })      
      mr.close()

    if what is None:
      oldpkgs.sort()
      newpkgs.sort()    
      return oldpkgs != newpkgs
    else:
      old = [ d[what] for d in oldpkgs ]
      new = [ d[what] for d in newpkgs ]
      old.sort()
      new.sort()
      return old != new
  
  def writeRepoContents(self, file):
    if exists(file):
      osutils.rm(file, force=True)
    os.mknod(file)
    mf = open(file, 'w')
    mwriter = csv.DictWriter(mf, ['file', 'size', 'mtime'], lineterminator='\n')
    for item in self.repoinfo:
      mwriter.writerow(item)
    mf.close()
    

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
