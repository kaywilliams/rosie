import os

from rendition import pps
from rendition import xmllib

from rendition.pps.constants import TYPE_DIR, TYPE_NOT_DIR

P = pps.Path

class IOMixin:
  def __init__(self):
    self.io = IOObject(self)

  def clean(self):
    self.io.clean_eventcache(all=True)

  def error(self, e):
    debugdir = self.mddir / 'debug'
    paths = self.mddir.listdir(all=True)
    debugdir.mkdirs()
    for path in paths: path.rename(debugdir/path.basename)

  def verify_output_exists(self):
    "all output files exist"
    for file in self.io.list_output():
      self.verifier.failUnlessExists(file)

class IOObject:
  "Dummy class to contain I/O-related methods"
  def __init__(self, ptr):
    self.ptr = ptr
    self.sync_items = {}
    self.chmod_items = {}

  def setup_sync(self, dst, xpaths=[], paths=[], id=None, iprefix=None, defmode=None):
    """
    Currently, setup_sync() can be called only after diff.setup() is
    called.

    @param xpaths  : list of xpath queries
    @param paths   : list of paths
    @param iprefix : the prefix to use for relative paths
    @param dst     : the location the files should be synced to
    @param id      : give an id to refer to these input files with. If
                     not specified, it defaults to the xpath query or
                     the path to the file.
    @param defmode : default mode of the file/directory

    @return inputs : [input file, ...]
    @return outputs: [output file, ...]
    """
    iprefix = P(iprefix or P(self.ptr._config.file).dirname)
    dst = P(dst)

    if not hasattr(paths,  '__iter__'): paths  = [paths]
    if not hasattr(xpaths, '__iter__'): xpaths = [xpaths]

    inputs = []
    outputs = []

    for x in xpaths:
      for item in self.ptr.config.xpath(x,[]):
        s = P(item.get('text()'))
        if isinstance(s, pps.path.file.FilePath): #! bad
          s = iprefix / s
        d = dst // P(item.get('@dest', ''))
        f = item.get('@filename', s.basename)
        m = item.get('@mode', defmode)

        inputs.append(s)
        outputs.extend(self._setup_sync(s, d, f, id or x, m))

    for s in paths:
      assert isinstance(s, str)
      if isinstance(s, pps.path.file.FilePath): #! bad
        s = iprefix / s
      f = s.basename

      inputs.append(s)
      outputs.extend(self._setup_sync(s, dst, f, id or s, defmode))

    return inputs, outputs

  def _setup_sync(self, sourcefile, dstdir, filename, id,  defmode):
    if not sourcefile.exists():
      raise IOError("missing input file(s) %s" % sourcefile)
    if sourcefile not in self.ptr.diff.handlers['input'].idata:
      self.ptr.diff.handlers['input'].idata.append(sourcefile)

    rtn = []
    self.sync_items.setdefault(id, set())
    self.chmod_items.setdefault(id, set())
    for src in sourcefile.findpaths():
      output_file = (dstdir/filename/src.relpathfrom(sourcefile)).normpath()
      self.chmod_items[id].add((output_file,
          int(defmode or oct((src.stat().st_mode & 0777) or 0644), 8)))
      if src.isfile():
        self.sync_items[id].add((src.normpath(), output_file))
        if output_file not in self.ptr.diff.handlers['output'].odata:
          self.ptr.diff.handlers['output'].odata.append(output_file)
        rtn.append(output_file)
    return rtn

  def sync_input(self, callback=None, link=False, what=None,
                 cache=False, text='downloading files', **kwargs):
    """
    Sync the input files to their output locations.

    @param link : if action is not specified, and link is True the
                  input files are linked to the output location.
    @param what : list of IDs identifying what to download.
    @param text : text to display prior to beginning sync operation.
    """
    if what is None:
      what = self.sync_items.keys()
    elif not hasattr(what, '__iter__'):
      what = [what]

    sync_items = set()
    chmod_items = set()

    for id in what:
      if not self.sync_items.has_key(id):
        continue
      for src,dst in self.sync_items[id]:
        if not dst.exists() or \
               self.ptr.diff.handlers['input'].diffdict.has_key(src) or \
               self.ptr.diff.handlers['output'].diffdict.has_key(dst):
          dst.rm(recursive=True, force=True)
          sync_items.add((src, dst))
      for dst,mode in self.chmod_items[id]:
        chmod_items.add((dst, mode))

    outputs = []
    if sync_items:
      sync_items = sorted(sync_items, cmp=lambda x, y: cmp(x[1].basename, y[1].basename))
      if callback: cb = callback
      elif cache:  cb = self.ptr.cache_callback
      elif link:   cb = self.ptr.link_callback
      else:        cb = self.ptr.copy_callback
      # perhaps sync_start and sync_end callbacks could be pushed into lower 
      # level functions, then we wouldn't have to figure out the default 
      # callback in both places
      cb.sync_start(text=text, count=len(sync_items))
      for src, dst in sync_items:
        # I'd rather handle arg passing a little better
        if cache:
          self.ptr.cache(src, dst, link=link, callback=cb, **kwargs) #!
        elif link:
          self.ptr.link(src, dst, callback=cb, **kwargs) #!
        else:
          self.ptr.copy(src, dst, callback=cb, **kwargs) #!
        outputs.append(dst)
      cb.sync_end()

    for file, mode in chmod_items:
      file.chmod(mode)

    return sorted(outputs)

  def clean_eventcache(self, all=False, callback=None):
    """
    Cleans event cache folder.

    @param all : If all is True, removes all files, else, removes
                 files that are not listed in the output section of
                 the event metadata file.
    """
    if all:
      self.ptr.mddir.listdir(all=True).rm(recursive=True)
    else:
      if self.ptr.mdfile.exists() and \
         self.ptr.diff.handlers.has_key('output'):
        self.ptr.diff.handlers['output'].clear()
        root = xmllib.tree.read(self.ptr.mdfile)
        self.ptr.diff.handlers['output'].mdread(root)
        expected = set()
        for path in self.ptr.diff.handlers['output'].oldoutput.keys():
          for item in path.findpaths(type=TYPE_NOT_DIR):
            expected.add(item)
        expected.add(self.ptr.mdfile)
        existing = set(self.ptr.mddir.findpaths(mindepth=1, type=TYPE_NOT_DIR))

        cb = callback or self.ptr.copy_callback
        obsolete_files = existing.difference(expected)
        if obsolete_files:
          cb.rm_start()
          for path in obsolete_files:
            cb.rm(path)
            path.rm(recursive=True, force=True)

        dirs = [ d for d in self.ptr.mddir.findpaths(mindepth=1, type=TYPE_DIR) if \
                 not d.findpaths(type=TYPE_NOT_DIR) ]
        if dirs:
          cb.rmdir_start()
          dirs.reverse()
          for dir in dirs:
            cb.rmdir(dir)
            dir.removedirs()

  def list_output(self, what=None):
    """
    list_output(source)

    Returns the list of output files corresponding to an input
    file/directory.

    @param what: a list of IDs of the files for which the output files
                 list is requested. If None, all output files are
                 returned.
    """
    if not self.ptr.diff.handlers.has_key('output'): return []
    if what is None:
      return self.ptr.diff.handlers['output'].odata
    if not hasattr(what, '__iter__'): what = [what]
    rtn = []
    for id in what:
      if not self.sync_items.has_key(id):
        continue
      for _,d in self.sync_items[id]:
        rtn.append(d)
    return sorted(rtn)
