""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

import csv
import os
import urllib2
import xml.sax

from gzip     import GzipFile
from os.path  import exists, isfile, join
from urlparse import urlparse, urlunparse

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
    self.files_callback = FilesCallback(self)
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

  def copy(self, src, dest, link=False):
    osutils.mkdir(dest, parent=True)
    if link: sync.link.sync(src, dest)
    else:    sync.sync(src, dest)    
    
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
      self.add_handler(InputHandler(data['input']))
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

  def var_changed_from_true(self, var):
    if not self.handlers['variables']:
      raise RuntimeError("No variables metadata handler")
    if self.handlers['variables'].diffdict.has_key(var) and \
       self.handlers['variables'].vars.has_key(var) and \
       self.handlers['variables'].vars[var]:
      return True
    else:
      return False
  
  def write_metadata(self):
    self.DT.write_metadata()

  def setup_sync(self, xpaths=[], paths=[], iprefix=None, id=None):
    """
    setup_sync([xpaths[,paths]])

    Currently, setup_sync() can be called only after setup_diff() is called.
    This will get fixed once the location of the metadata file can be
    programmatically determined.
    
    @param xpaths  : [(xpath query,  output prefix), ...]
    @param paths   : [(path to file, output prefix), ...]
    @param iprefix : the prefix to use for relative paths
    @param id      : give an id to refer to these input files with. If
                     not specified, it defaults to the xpath query or
                     the path to the file. 

    @return outputs: [(output file, source file),...]
    """
    iprefix = iprefix or osutils.dirname(self.config.file)
    
    if paths and type(paths) != type([]):
      paths = [paths]
    if xpaths and type(xpaths) != type([]):
      xpaths = [xpaths]
                
    if not self.handlers.has_key('input'):
      self.add_handler(InputHandler([]))

    outputs = []
    for x,o in xpaths:
      i = id or x
      for item in self.config.xpath(x,[]):
        s = item.get('text()')
        d = item.get('@dest', '')
        if s.startswith('file://'): s = s[7:]
        if not s.startswith('/') and s.find('://') == -1:
          s = join(iprefix, s)
        d = join(o, d.lstrip('/'))
        outputs.extend(self._setup_sync(s, d, i))

    for p,o in paths:
      i = id or p
      if type(p) != type([]):
        p = [p]
      for item in p:
        if type(item) == type(()):
          if item[0].startswith('file://'):
            item = (item[0][7:], item[1], item[2])
          elif item[0].startswith('/') and item[0].find('://') == -1:
            item = (join(iprefix, item[0]), item[1], item[2])
        else:
          if item.startswith('file://'): item = item[7:]
          if not item.startswith('/') and item.find('://') == -1:
            item = join(iprefix, item)
        outputs.extend(self._setup_sync(item, o, i))

    return outputs

  def _setup_sync(self, sourcefile, destdir, id):
    rtn = []
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
          site = urllib2.urlopen(sourcefile)
          site.close()
        except Exception, e:
          raise IOError("missing input file(s) %s" % sourcefile)

    for f in inputs:
      if not self.syncinfo.has_key(id):
        self.syncinfo[id] = {}
      if not self.syncinfo[id].has_key(f):
        self.syncinfo[id][f] = []
      ofile = join(destdir, f[sourcefile.rstrip('/').rfind('/')+1:])
      self.syncinfo[id][f].append(ofile)
      rtn.append((ofile, f))
    return rtn

  def remove_output(self, rmlist=None, all=False, cb=None):
    """
    remove_output([all[,cb]])

    Remove output files.
    @param all  : If all is True, remove all output files, else remove
                  the files that have changed.
    """
    if rmlist is None:
      if all:
        rmlist = self.handlers['output'].oldoutput.keys()
      else:
        rmlist = []
        # remove previous output files that have been modified
        # since last run
        rmlist.extend([ f for f,d in self.handlers['output'].diffdict.items() if d[0] is not None ])
        
        # remove files the input of which has been modified
        if self.has_changed('input'):
          self.handlers['output'].refresh()
          for ofile, ifile in self.handlers['output'].odata:
            if ofile not in rmlist and self.handlers['input'].diffdict.has_key(ifile):
              rmlist.append(ofile)
              
        # remove output files from the last time that aren't needed
        # anymore
        for oldfile in self.handlers['output'].oldoutput.keys():
          found = False
          
          for id in self.syncinfo.keys():
            for ds in self.syncinfo[id].values():
              if oldfile in ds:
                found = True
                break
            if found:
              break
            
          if not found and oldfile not in rmlist:
            rmlist.append(oldfile)
            
      rmlist = [ r for r in rmlist if exists(r) ]

    if not rmlist:
      return

    cb = cb or self.files_callback
    cb.remove_start()

    rmlist.sort(lambda x,y: cmp(osutils.basename(x), osutils.basename(y)))
    dirs = []
    
    # delete the files, whether or not they exist
    for rmitem in rmlist:
      cb.remove(rmitem)
      dir = osutils.dirname(rmitem)
      if dir not in dirs:
        dirs.append(dir)

    dirs = [ d for d in dirs if not osutils.find(location=d,
                                                 type=osutils.TYPE_FILE|osutils.TYPE_LINK) ]    
    if not dirs: return
    dirs.reverse()
    cb.remove_dir_start()
    for dir in dirs:
      cb.remove_dir(dir)

  def sync_input(self, cb=None, link=False, what=None, copy=False):
    """
    sync_input([action[,cb]])
    
    Sync the input files to their output locations.

    @param link : if action is not specified, and link is True the
                  input files are linked to the output location.
    @param what : list of IDs identifying what to download.
    """
    if what is None: what = self.syncinfo.keys()
    if type(what) == type(''): what = [what]
      
    sync_items = []
    for id in what:
      if not self.syncinfo.has_key(id):
        continue
      for s,ds in self.syncinfo[id].items():
        for d in ds:
          if not exists(d):
            sync_items.append((s,d))

    if not sync_items: return

    sync_items.sort(lambda x, y: cmp(osutils.basename(x[1]), osutils.basename(y[1])))      

    outputs = []
    cb = cb or self.files_callback
    cb.sync_file_start()
    for s,d in sync_items:
      cb.sync_file(s, d, link=link, copy=copy)
      outputs.append(d)
    return outputs
  
  def list_output(self, what=None):
    """
    list_output(source)
    
    Returns the list of output files corresponding to an input file/directory.

    @param what: a list of IDs of the files for which the output files list is
                 requested. If None, all output files are returned.
    """
    if what is None:
      return [ f for f,_ in self.handlers['output'].odata ]
    rtn = []
    if type(what) != type([]): what = [what]
    for id in what:
      if not self.syncinfo.has_key(id):
        continue
      for ds in self.syncinfo[id].values():
        rtn.extend(ds)
    return rtn

#------- DIFFTEST HANDLERS -----#
class InputHandler:
  def __init__(self, data):
    self.name = 'input'
    self.idata = data
    
    self.oldinput = {} # {file: stats}
    self.newinput = {} # {file: stats}

    self.processed = [] # list of processed input data elements
    self.diffdict = {}  # {file: (old stats, new stats)}

    difftest.expand(self.idata)
        
  def clear(self):
    self.oldinput.clear()
      
  def mdread(self, metadata):    
    for file in metadata.xpath('/metadata/input/file'):
      self.oldinput[file.get('@path')] = (int(file.get('size/text()')),
                                          int(file.get('mtime/text()')))
      
  def mdwrite(self, root):
    try: root.remove(root.get('input'))
    except TypeError: pass
    parent = xmltree.Element('input', parent=root)
    for datum in self.idata:
      self.mdadd(datum)
    for i in self.newinput.keys():
      s,m = self.newinput[i]
      e = xmltree.Element('file', parent=parent, attrs={'path': i})
      xmltree.Element('size', parent=e, text=str(s))
      xmltree.Element('mtime', parent=e, text=str(m))
    
  def diff(self):
    for datum in self.idata:
      self.mdadd(datum)
    self.diffdict = difftest.diff(self.oldinput, self.newinput)    
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict

  def mdadd(self, input):
    if input in self.processed:
      return [ x for x in self.processed if x.startswith(input) ]
    
    if type(input) == type(()):
      i,s,m = input
      if i.startswith('file://'): i = i[7:]
      self.processed.append(i)
      self.newinput[i] = (s,m)
      return [i]
    else:
      inputs = []
      if input.startswith('file://'): input = input[7:]
      self.processed.append(input)
      for i,s,m in difftest.expandPaths(input):
        if i not in self.processed:
          self.processed.append(i)
        self.newinput[i] = (s,m)
        inputs.append(i)
      return inputs

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
    
    self.pkgsfile = None
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
    self.repoinfo = []    
    if repofile is None:
      pxml = GzipFile(filename=self.ljoin(self.repodata_path, 'repodata', self.primaryfile),
                      mode='rt')
      handler = PrimaryXmlContentHandler()
      self.parser.setContentHandler(handler)
      self.parser.parse(pxml)
      pxml.close()
      
      for f,s,m in handler.pkgs:
        self.repoinfo.append({
          'file':  self.rjoin(self.repodata_path, f),
          'size':  s,
          'mtime': m,
          })
      self.repoinfo.sort()
    else:
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
    

class PrimaryXmlContentHandler(xml.sax.ContentHandler):
  def __init__(self):
    xml.sax.ContentHandler.__init__(self)
    self.pkgs = []

    self.mtime = None
    self.size  = None
    self.loc   = None

    self.pkgstart = False
    
  def startElement(self, name, attrs):
    if name == 'package':
      self.pkgstart = True
    elif self.pkgstart and name == 'location':
      self.loc = str(attrs.get('href'))
    elif self.pkgstart and name == 'size':
      self.size = int(attrs.get('package'))
    elif self.pkgstart and name == 'time':
      self.mtime = int(attrs.get('file'))

  def endElement(self, name):
    if name == 'package':
      self.pkgstart = False
      self.pkgs.append((self.loc, self.size, self.mtime))

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
