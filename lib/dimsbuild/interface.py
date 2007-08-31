""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

import csv
import xml.sax

from gzip import GzipFile

from dims import pps
from dims import sync
from dims import xmltree

from dims.configlib import expand_macros
from dims.sync      import cache, link

from dimsbuild import difftest

from dimsbuild.callback  import BuildSyncCallback, FilesCallback
from dimsbuild.constants import BOOLEANS_TRUE

P = pps.Path

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
    cache_dir = P(self._base.mainconfig.get('/dimsbuild/cache/path/text()', None) or \
                  self.CACHE_DIR / '.cache')
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
  
  def cache(self, src, dst, link=False, force=False, **kwargs):
    self.cache_handler.force = force
    if link: self.cache_handler.cache_copy_handler = self.link_handler
    else:    self.cache_handler.cache_copy_handler = self.copy_handler
    
    if not kwargs.has_key('copy_handler'):
      kwargs['copy_handler'] = self.cache_handler
    if not kwargs.has_key('callback'):
      kwargs['callback'] = self.cache_callback
    
    dst.mkdirs()
    sync.sync(src, dst, **kwargs)

  def copy(self, src, dst, link=False):
    dst.mkdirs()
    if link: sync.link.sync(src, dst)
    else:    sync.sync(src, dst)    
    
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

  # DiffMixin items
  def setup_diff(self, mdfile, data):
    self.DT = difftest.DiffTest(mdfile)
    if data.has_key('input'):
      self.add_handler(difftest.InputHandler(data['input']))
    if data.has_key('output'):
      self.add_handler(difftest.OutputHandler(data['output']))
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
    iprefix = P(iprefix or P(self.config.file).dirname)
    
    if not hasattr(paths,  '__iter__'): paths  = [paths]
    if not hasattr(xpaths, '__iter__'): xpaths = [xpaths]
                
    if not self.handlers.has_key('input'):
      self.add_handler(InputHandler([]))

    outputs = []
    for x,o in xpaths:
      i = id or x
      for item in self.config.xpath(x,[]):
        s = P(item.get('text()'))
        d = P(item.get('@dest', ''))
        if isinstance(s, pps.path.file.FilePath):
          s = iprefix / s
        d = P(o) / d.lstrip('/')
        outputs.extend(self._setup_sync(s, d, i))
    
    for p,o in paths:
      i = id or p
      if isinstance(p, tuple):
        raise ValueError("Fix me!")
      if isinstance(p, tuple):
        file, size, mtime = p
        if isinstance(file, pps.path.file.FilePath):
          file = iprefix / file
        p = (P(file), size, mtime)
      else:
        assert isinstance(p, str)
        if isinstance(p, pps.path.file.FilePath):
          p = iprefix / p
        p = P(p)
      o = P(o)
      outputs.extend(self._setup_sync(p, o, i))
    
    return outputs

  def _setup_sync(self, sourcefile, dstdir, id):
    rtn = []
    
    self.handlers['input'].idata.append(sourcefile)

    if isinstance(sourcefile, tuple):
      sourcefile = sourcefile[0]
    
    if not sourcefile.exists():
      raise IOError("missing input file(s) %s" % sourcefile)
    
    for f in sourcefile.findpaths(type=pps.constants.TYPE_FILE | \
                                       pps.constants.TYPE_LINK):
      if not self.syncinfo.has_key(id):
        self.syncinfo[id] = {}
      if not self.syncinfo[id].has_key(f):
        self.syncinfo[id][f] = []
      ofile = dstdir / f.tokens[len(sourcefile.tokens)-1:]
      self.syncinfo[id][f].append(ofile)
      rtn.append(ofile)
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
            
      rmlist = [ r for r in rmlist if r.exists() ]

    if not rmlist:
      return

    cb = cb or self.files_callback
    cb.remove_start()

    rmlist.sort(lambda x,y: cmp(x.basename, y.basename))
    dirs = []
    
    # delete the files, whether or not they exist
    for rmitem in rmlist:
      cb.remove(rmitem)
      rmitem.rm(recursive=True, force=True)
      dir = rmitem.dirname
      if dir not in dirs:
        dirs.append(dir)

    dirs = [ d for d in dirs if not d.findpaths(type=pps.constants.TYPE_FILE | \
                                                     pps.constants.TYPE_LINK) ]
    
    if not dirs: return
    dirs.reverse()
    cb.remove_dir_start()
    for dir in dirs:
      cb.remove_dir(dir)
      dir.removedirs()
  
  def sync_input(self, cb=None, link=False, what=None, copy=False):
    """ 
    sync_input([action[,cb]])
    
    Sync the input files to their output locations.

    @param link : if action is not specified, and link is True the
                  input files are linked to the output location.
    @param what : list of IDs identifying what to download.
    """
    if what is None: what = self.syncinfo.keys()
    if not hasattr(what, '__iter__'): what = [what]
      
    sync_items = []
    for id in what:
      if not self.syncinfo.has_key(id):
        continue
      for s,ds in self.syncinfo[id].items():
        for d in ds:
          if not d.exists():
            sync_items.append((s,d))

    if not sync_items: return

    sync_items.sort(lambda x, y: cmp(x[1].basename, y[1].basename))

    outputs = []
    cb = cb or self.files_callback
    cb.sync_file_start()
    for s,d in sync_items:
      if copy: self.copy(s, d.dirname, link=link)
      else:    self.cache(s, d.dirname, link=link)
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
      return self.handlers['output'].odata
    rtn = []
    if not hasattr(what, '__iter__'): what = [what]
    for id in what:
      if not self.syncinfo.has_key(id):
        continue
      for ds in self.syncinfo[id].values():
        rtn.extend(ds)
    return rtn


#------- CLASSES ---------#
class Repo:
  def __init__(self, id):
    self.id = id
    
    self.remote_path = None
    self.local_path = None

    self.gpgcheck = False
    self.gpgkey = None
    
    self.username = None
    self.password = None
    
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
  
  def rjoin(self, *args):
    p = self.remote_path
    for arg in args: p = p / arg
    return p
  
  def ljoin(self, *args):
    p = self.local_path
    for arg in args: p = p / arg
    return p
  
  def readRepoData(self, repomd=None):
    repomd = repomd or xmltree.read(self.ljoin(self.repodata_path, self.mdfile)).xpath('//data')
    for data in repomd:
      repofile = P(data.get('location/@href'))
      filetype = data.get('@type')
      if   filetype == 'group':     self.groupfile     = repofile.basename
      elif filetype == 'primary':   self.primaryfile   = repofile.basename
      elif filetype == 'filelists': self.filelistsfile = repofile.basename
      elif filetype == 'other':     self.otherfile     = repofile.basename
  
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
      mr = repofile.open('r')
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

    if oldfile.isfile():
      mr = oldfile.open('r')
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
    if file.exists():
      file.rm()
    file.touch()
    mf = file.open('w')
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
  repo.remote_path   = P(xml.get('path/text()'))
  repo.gpgcheck      = xml.get('gpgcheck/text()', 'False') in BOOLEANS_TRUE
  repo.gpgkey        = xml.get('gpgkey/text()', None)
  repo.repodata_path = xml.get('repodata-path/text()', '')
  repo.include       = xml.get('include/package/text()', [])
  repo.exclude       = xml.get('exclude/package/text()', [])
  
  return repo
