from dims import pps

P = pps.Path

class IOMixin:
  def __init__(self):
    self.io = IOObject(self)
  
  def clean(self):
    self.io.remove_output(all=True)


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
  
  def remove_output(self, rmlist=None, all=False, cb=None):
    """ 
    Remove output files.
    @param all  : If all is True, remove all output files, else remove
                  the files that have changed.
    """
    if not self.ptr.diff.handlers.has_key('output'): return
    
    if rmlist is None:
      if all:
        rmlist = self.ptr.diff.handlers['output'].oldoutput.keys()
      else:
        rmlist = []
        # remove previous output files that have been modified
        # since last run
        rmlist.extend([ f for f,d in self.ptr.diff.handlers['output'].diffdict.items() if d[0] is not None ])
        
        # remove output files from the last time that aren't needed
        # anymore
        for oldfile in self.ptr.diff.handlers['output'].oldoutput.keys():
          found = False
          
          for id in self.sync_info.keys():
            for ds in self.sync_info[id].values():
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
    
    cb = cb or self.ptr.files_callback
    cb.rm_start()
    
    rmlist.sort()
    dirs = []
    
    # delete the files, whether or not they exist
    for rmitem in rmlist:
      cb.rm(rmitem)
      rmitem.rm(recursive=True, force=True)
      dir = rmitem.dirname
      if dir not in dirs:
        dirs.append(dir)
    
    dirs = [ d for d in dirs if \
             not d.findpaths(type=pps.constants.TYPE_NOT_DIR) ]
    
    if not dirs: return
    dirs.reverse()
    cb.rmdir_start()
    for dir in dirs:
      cb.rmdir(dir)
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
