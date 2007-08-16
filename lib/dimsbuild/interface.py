""" 
interface.py
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 5th, 2007'

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

from dimsbuild.callback  import BuildSyncCallback
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

    # download stuff
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
  
  def has_changed(self, name):
    if not self.handlers.has_key(name):
      raise RuntimeError("unknown handler accessed: '%s'" % name)    
    if not self.diffset.has_key(name):
      self.diffset[name] = (len(self.handlers[name].diff()) > 0)
    return self.diffset[name]
  
  def write_metadata(self):
    self.DT.write_metadata()

  def remove_output(self, parent=None, rmlist=None, all=False, message="removing files"):
    """
    remove_output(parent[,all[,message]])

    Remove output files.

    @param parent : the parent directory of the files. If None, it is
                    the file's parent directory.
    @param all    : If all is True, remove all output files, else remove
                    the files that have changed.
    """
    if rmlist is None:
      if all:
        rmlist = self.handlers['output'].oldoutput.keys()
      else:
        # remove files that have been altered, the source of the file has modified, or
        # the file is no longer needed.
        rmlist = []
        if self.has_changed('output'):
          rmlist.extend([ f for f,d in self.handlers['output'].odiff.items() if d[0] is not None ])
        if self.has_changed('input'):
          for source, file in self.handlers['output'].odata:
            if file not in rmlist and self.handlers['input'].idiff.has_key(source):
              rmlist.append(file)
        for oldfile in self.handlers['output'].oldoutput.keys():
          found = False
          for ds in self.syncinfo.values():
            if oldfile in ds:
              found = True
          if not found:
            rmlist.append(oldfile)
      rmlist = [ r for r in rmlist if exists(r) ]
            
    if not rmlist: return
    
    self.log(1, message)
    rmlist.sort()
    dirs = []
    # delete the files, whether or not they exist
    for rmitem in rmlist:
      self.log(2, osutils.basename(rmitem))
      osutils.rm(rmitem, recursive=True, force=True)
      dir = osutils.dirname(rmitem)
      if dir not in dirs and \
             (parent and dir != parent.rstrip('/')):
        dirs.append(dir)

    if not dirs: return 

    dirs.sort()
    ubound = len(dirs)
    # filter subdirectories
    for i in xrange(ubound-1):
      for j in xrange(i+1, ubound):
        if dirs[j].startswith(dirs[i]):
          dirs.pop(j)    

    # delete empty directories, if any exist
    dirs = [ d for d in dirs if not osutils.find(d, type=osutils.TYPE_FILE|osutils.TYPE_LINK) ]
    if dirs:
      self.log(1, "removing empty directories")
      for d in dirs:
        self.log(2, osutils.basename(d))
        osutils.rm(d, recursive=True, force=True)  
      
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
    newio = {}
    for x,i,o in xpaths:
      for item in self.config.xpath(x,[]):
        s = item.get('text()')
        d = item.get('@dest', '')
        if s.startswith('file://'): s = s[7:]
        if not s.startswith('/') and s.find('://') == -1:
          s = join(i,s)
        d = join(o, d.lstrip('/'))
        if not newio.has_key(s): newio[s] = []
        newio[s].append(d)

    for p,o in paths:
      if type(p) == type(''): p = [p]
      for item in p:
        if item.startswith('file://'): item = item[7:]
        if not newio.has_key(item): newio[item] = []
        newio[item].append(o)

    outputs = []
    for s in newio.keys():
      for d in newio[s]:
        if not self.handlers['input'].filelists.has_key(s):
          self.handlers['input'].filelists[s] = difftest.expandPaths(s)
        ifiles = self.handlers['input'].filelists[s]
        if not ifiles:
          if s.find('://') == -1 and not exists(s):
            raise IOError("missing input file(s) %s" % s)
          else:
            ## TODO if source is 404'd raise exception
            pass
        for ifile in self.handlers['input'].filelists[s]:
          if not self.syncinfo.has_key(ifile): self.syncinfo[ifile] = []
          ofile = (join(d, ifile[s.rstrip('/').rfind('/')+1:]))
          self.syncinfo[ifile].append(ofile)
          outputs.append((ofile, ifile))
          
    return self.syncinfo.keys(), outputs

  def list_output(self, source):
    """
    list_output(source)
    
    Returns the list of output files corresponding to an input file/directory.

    @param source: the source file for which the output files' list is
                   requested.    
    """
    return [ d for d,s in self.handlers['output'].odata if s is not None and s.startswith(source) ]
    
  def sync_input(self, action=None, message="downloading input files"):
    """
    sync_input([action[,message]])
    
    Sync the input files to their output locations.
    
    @param action: the function to call with the source file and
                   destination as parameters. If None, simply sync the
                   source file to the destination.
    """
    if not self.syncinfo:
      self.log(4, "nothing to sync")
      return
    
    self.log(1, message)
    for s,ds in self.syncinfo.items():
      for d in ds:
        d = osutils.dirname(d)
        if action: action(s,d)
        else:      self.cache(s,d)

#------- DIFFTEST HANDLERS -----#
class OutputHandler:
  def __init__(self, data):
    self.name  = 'output'
    self.odata = data
    self.oldoutput = {}
    self.odiff = {}

    self.refresh()
    
  def refresh(self):
    torem = []
    toapp = []

    for datum in self.odata:
      if type(datum) == type(''):
        torem.append(datum)
        toapp.append((datum, None))
      if type(datum) == type([]):
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
      paths = difftest.expandPaths(file)
      if paths:
        for output in paths:
          size, mtime = difftest.DiffTuple(output)
          attrs = {'path': output}          
          e = xmltree.Element('file', parent=parent, attrs=attrs)
          xmltree.Element('size', parent=e, text=str(size))
          xmltree.Element('mtime', parent=e, text=str(mtime))
          if source:
            xmltree.Element('source', parent=e, text=source)

  def diff(self):
    self.refresh()
    newitems = {}
    for file in self.oldoutput.keys():
      size, mtime = difftest.DiffTuple(file)
      newitems[file] = (size, mtime, self.oldoutput[file][2])
    self.odiff = difftest.diff(self.oldoutput, newitems)
    if self.odiff: self.dprint(self.odiff)
    return self.odiff

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
    pxml = GzipFile(filename=self.ljoin(self.repodata_path, 'repodata', self.primaryfile),
                    mode='rt')
    
    handler = PrimaryXmlContentHandler()
    self.parser.setContentHandler(handler)
    self.parser.parse(pxml)

    pxml.close()
    
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
