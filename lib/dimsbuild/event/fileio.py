from dims import pps

from dims.xml import tree as xmltree

from dims.pps.constants import TYPE_DIR, TYPE_NOT_DIR

P = pps.Path

class IOMixin:
  def __init__(self):
    self.io = IOObject(self)

  def clean(self):
    self.io.clean_eventcache(all=True)

class IOObject:
  "Dummy class to contain I/O-related methods"
  def __init__(self, ptr):
    self.ptr = ptr
    self.sync_info = {}
  
  # former FilesMixin stuff
  def setup_sync(self, dst, xpaths=[], paths=[], id=None, iprefix=None):
    """ 
    Currently, setup_sync() can be called only after diff.setup() is called.
    This will get fixed once the location of the metadata file can be
    programmatically determined.
    
    @param xpaths  : list of xpath queries
    @param paths   : list of paths
    @param iprefix : the prefix to use for relative paths
    @param dst     : the location the files should be synced to
    @param id      : give an id to refer to these input files with. If
                     not specified, it defaults to the xpath query or
                     the path to the file. 
    
    @return inputs : [input file, ...]
    @return outputs: [output file, ...]
    """
    iprefix = P(iprefix or P(self.ptr.config.file).dirname)
    dst = P(dst)
    
    if not hasattr(paths,  '__iter__'): paths  = [paths]
    if not hasattr(xpaths, '__iter__'): xpaths = [xpaths]
    
    inputs = []
    outputs = []
    
    for x in xpaths:
      for item in self.ptr.config.xpath(x,[]):
        s = P(item.get('text()'))
        d = P(item.get('@dest', ''))
        if isinstance(s, pps.path.file.FilePath): #! bad
          s = iprefix / s
        src = P(s)
        dst = dst / d.lstrip('/')
        inputs.append(src)
        outputs.extend(self._setup_sync(src, dst, id or x))
    
    for s in paths:
      assert isinstance(s, str)
      if isinstance(s, pps.path.file.FilePath): #! bad
        s = iprefix / s
      src = P(s)
      inputs.append(src)
      outputs.extend(self._setup_sync(src, dst, id or s))
    
    return inputs, outputs
  
  def _setup_sync(self, sourcefile, dstdir, id):
    if not sourcefile.exists():
      raise IOError("missing input file(s) %s" % sourcefile)
    rtn = []
    self.ptr.diff.handlers['input'].idata.append(sourcefile)
    for f in sourcefile.findpaths(type=pps.constants.TYPE_NOT_DIR):
      if not self.sync_info.has_key(id):
        self.sync_info[id] = {}
      if not self.sync_info[id].has_key(f):
        self.sync_info[id][f] = []
      ofile = dstdir / f.tokens[len(sourcefile.tokens)-1:]
      self.sync_info[id][f].append(ofile)
      self.ptr.diff.handlers['output'].odata.append(ofile)
      rtn.append(ofile)
    return rtn

  def clean_eventcache(self, all=False):
    """ 
    Cleans event cache folder. 
    @param all  : If all is True, removes all files, else, removes files that 
                  are not listed in the output section of the event metadata file.
    """
    if all:
      self.ptr.mddir.listdir(all=True).rm(recursive=True, force=True)
    else:
      if self.ptr.diff.handlers.has_key('output'):
        self.ptr.diff.handlers['output'].clear()
        root = xmltree.read(self.ptr.mdfile)
        self.ptr.diff.handlers['output'].mdread(root)
        expected = set()
        for path in self.ptr.diff.handlers['output'].oldoutput.keys():
          for item in path.findpaths(type=TYPE_NOT_DIR):
            expected.add(item)
        expected.add(self.ptr.mdfile)
        existing = set(self.ptr.mddir.findpaths(mindepth=1, type=TYPE_NOT_DIR))
        for path in existing.difference(expected):
          path.rm(recursive=True, force=True)
        # remove empty dirs
        dirs = [ d for d in self.ptr.mddir.findpaths(mindepth=1, type=TYPE_DIR) if \
               not d.findpaths(type=TYPE_NOT_DIR) ]
        if not dirs: return
        dirs.reverse()
        for dir in dirs:
          dir.removedirs()
  
  def sync_input(self, cb=None, link=False, what=None, copy=False):
    """ 
    Sync the input files to their output locations.
    
    @param link : if action is not specified, and link is True the
                  input files are linked to the output location.
    @param what : list of IDs identifying what to download.
    """
    if what is None: what = self.sync_info.keys()
    if not hasattr(what, '__iter__'): what = [what]
    
    sync_items = []
    for id in what:
      if not self.sync_info.has_key(id):
        continue
      for s,ds in self.sync_info[id].items():
        for d in ds:
          if self.ptr.diff.handlers['input'].diffdict.has_key(s) or not d.exists():
            sync_items.append((s,d))
    
    if not sync_items: return
    
    sync_items.sort(lambda x, y: cmp(x[1].basename, y[1].basename))
    
    outputs = []
    cb = cb or self.ptr.files_callback
    cb.sync_start()
    for s,d in sync_items:
      if copy: self.ptr.copy(s, d.dirname, link=link)
      else:    self.ptr.cache(s, d.dirname, link=link)
      outputs.append(d)
    return sorted(outputs)
  
  def list_output(self, what=None):
    """ 
    list_output(source)
    
    Returns the list of output files corresponding to an input file/directory.
    
    @param what: a list of IDs of the files for which the output files list is
                 requested. If None, all output files are returned.
    """
    if what is None:
      return self.ptr.diff.handlers['output'].odata
    rtn = []
    if not hasattr(what, '__iter__'): what = [what]
    for id in what:
      if not self.sync_info.has_key(id):
        continue
      for ds in self.sync_info[id].values():
        rtn.extend(ds)
    return sorted(rtn)
