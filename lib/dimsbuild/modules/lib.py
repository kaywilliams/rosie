from os.path import abspath, exists, isdir, join

from dims import listcompare
from dims import osutils

from dimsbuild import difftest

def removeFiles(rmlist, parent, logger):
  if type(rmlist) == str: rmlist = [rmlist]
  rmlist.sort()
  emptydirs = []
  for item in rmlist:
    # remove the items in the rmlist as soon as possible, so that
    # all empty directories can be computed. Once an item is
    # deleted, its parent directories are checked to see if they are
    # empty, and if they are, they are deleted (this is what the
    # while-loop does).
    # this is very inefficient #!
    if isdir(item) and osutils.find(item, type=osutils.TYPE_FILE|osutils.TYPE_LINK):
      # don't mess with directories that have files in them
      continue
    
    if exists(item):
      logger(2, item[len(parent):].strip('/'))      
      osutils.rm(item, recursive=True, force=True)
      
    item = osutils.dirname(item)    
    while not osutils.find(item, type=osutils.TYPE_FILE|osutils.TYPE_LINK):
      if item.lstrip('/') == parent.lstrip('/'):
        # if upper-bound is reached, break out of loop.
        break
      emptydirs.append(item)
      item = osutils.dirname(item)
      
  emptydirs.sort()
  if emptydirs:
    logger(1, "removing empty directories")
    for item in emptydirs:
      if exists(item):
        logger(2, item[len(parent):].lstrip('/'))
        osutils.rm(item, recursive=True, force=True)
        
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
    self.handlers = {}
    self.diffset = {}
    
    if self.data.has_key('input'):
      h = difftest.InputHandler(self.data['input'])
      self.DT.addHandler(h)
      self.handlers[h.name] = h
    if self.data.has_key('output'):
      h = difftest.OutputHandler(self.data['output'])
      self.DT.addHandler(h)
      self.handlers[h.name] = h
    if self.data.has_key('variables'):
      h = difftest.VariablesHandler(self.data['variables'], self)
      self.DT.addHandler(h)
      self.handlers[h.name] = h      
    if self.data.has_key('config'):
      h = difftest.ConfigHandler(self.data['config'], self.interface.config)
      self.DT.addHandler(h)
      self.handlers[h.name] = h      

  def update(self, datadict):
    for dtype in datadict:
      if self.handlers.has_key(dtype):
        self.handlers[dtype].update(datadict[dtype])

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
  
  def changed(self, name):
    if not self.handlers.has_key(name):
      raise RuntimeError("unknown handler accessed: '%s'" % name)    
    if not self.diffset.has_key(name):
      self.diffset[name] = (len(self.handlers[name].diff()) > 0)
    return self.diffset[name]
  
  def write_metadata(self):
    self.DT.write_metadata()

class FilesMixin:
  def __init__(self, parentdir):
    self.parentdir = parentdir.rstrip('/') # make sure there is no trailing slash
    self.info = {}
    
  def add_files(self,
                xpaths=None,
                paths=None,
                addinput=True,
                addoutput=True,
                iprefix=None,
                oprefix=None):
    """ 
    @param xpaths    : a list of xpath queries to the path elements    
    @param paths     : a list of 2-tuples: (src, dest). If dest is None it
                       is set to self.parentdir
    @param addinput  : add the list of input files to the input
                       handler's data    
    @param addoutput : add the list of output files to the output
                       handler's data    
    @param iprefix   : the prefix to use for the input files instead of
                       the directory of the config file                       
    @param oprefix   : the prefix to use for the output files instead of
                       self.parentdir    
    """
    iprefix = iprefix or osutils.dirname(abspath(self.interface.config.file))
    oprefix = oprefix or self.parentdir

    if xpaths:
      self._process_xpaths(xpaths, iprefix, oprefix, self.__add_item)
    if paths:
      self._process_paths(paths, iprefix, oprefix, self.__add_item)
    
    if addinput:
      # we don't know if self.update exists, unless DictMixin is also imported #!
      self.update({
        'input':  self.info.values(),
      })
    if addoutput:
      self.update({
        'output': self.info.keys(),
      })    

  def compute(self, ifile):
    "Compute the output file(s), given the input file/directory."    
    ifile = ifile.rstrip('/')
    outputs = []
    for ofile in self.info.keys():
      if self.info[ofile].startswith(ifile):
        outputs.append(ofile)
    return outputs
    
  def sync_files(self,
                 action=None,
                 message="downloading input files"):
    """ 
    Sync the input files to their output locations.
    
    @param action: the function to call with the source file and
                   destination as parameters. If None, simply sync the
                   source file to the destination.
    """
    if not self.info:
      self.interface.log(4, "nothing to sync")
      return
    
    self.interface.log(1, message)

    for dst, src in self.info.items():
      dst = osutils.dirname(dst)
      if action:
        action(src, dst)
      else:
        self.__sync_item(src, dst)
  
  def remove_files(self,
                   rmlist=[],
                   message="removing files"):
    "Remove obsolete/modified files and delete empty directories."
    if not rmlist:
      rmlist = []
      # remove output files that are no longer required
      for f,d in self.handlers['output'].diffdict.items():
        if d[0] is not None:
          rmlist.append(f)

      # remove output files the source of which has changed
      for f in self.handlers['input'].diffdict:
        if self.info.has_key(f):
          rmlist.append(self.info[f][1])

      if not rmlist:
        return
      
    self.interface.log(1, message)

    removeFiles(rmlist, self.parentdir, self.interface.log)
    
  def _process_xpaths(self, xpaths, iprefix, oprefix, action):
    """ 
    Read the xpath queries specified by the xpaths parameter. For
    each of the elements found, the text node's value is the source
    and the value of the 'dest' attribute is the destination (or
    prefix if no such attribute is found).    
    """
    if type(xpaths) == str: xpaths = [xpaths]

    paths = []
    for xpath in xpaths:
      for path in self.interface.config.xpath(xpath, []):
        src = path.get('text()')
        dest = path.get('@dest', None)
        paths.append((src, dest))

    self._process_paths(paths, iprefix, oprefix, action)

  def _process_paths(self, paths, iprefix, oprefix, action):
    """ 
    Add paths specified by the info parameter which is a list of
    tuples with the source as the first element and the destination as
    the second. If info element is not a list, it is converted to
    one.
    """
    npaths = []

    if type(paths) != list: paths = [paths]
    
    for item in paths:
      if type(item) == str:
        src, dest = item, None
      else:
        assert type(item) == tuple
        src, dest = item

      if src.startswith('file://'):
        src = src[7:]
      
      if iprefix and src.find('://') == -1:
        src = join(iprefix, src)

      if dest is None:
        dest = oprefix
      else:
        dest = join(oprefix, dest.lstrip('/'))
      npaths.append((src, dest))
      
    for s,d in npaths:
      action(s,d)
      
  def __sync_item(self, src, dst):
    self.interface.cache(src, dst)

  def __add_item(self, src, dst):
    if not self.handlers['input'].filelists.has_key(src):
      self.handlers['input'].filelists[src] = difftest.expandPaths(src)      
    
    ifiles = self.handlers['input'].filelists[src]
    if not ifiles:
      raise RuntimeError("missing input file(s): %s" % src)

    for ifile in ifiles:
      # populate {output: input} mapping
      self.info[join(dst, ifile[src.rstrip('/').rfind('/')+1:])] = ifile
