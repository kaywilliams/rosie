import os

from dims import pps
from dims import xmllib

from dims.pps.constants import TYPE_DIR, TYPE_NOT_DIR

P = pps.Path

class IOMixin:
  def __init__(self):
    self.io = IOObject(self)

  def clean(self):
    self.io.clean_eventcache(all=True)

  def error(self, e):
    debugdir = self.mddir / '.debug'
    paths = self.mddir.listdir(all=True)
    debugdir.mkdirs()
    for path in paths: path.rename(debugdir/path.basename)

class IOObject:
  "Dummy class to contain I/O-related methods"
  def __init__(self, ptr):
    self.ptr = ptr
    self.sync_info = {}

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
        d = P(item.get('@dest', ''))
        m = item.get('@mode', None) or defmode
        if isinstance(s, pps.path.file.FilePath): #! bad
          s = iprefix / s
        s = P(s)
        d = dst / d.lstrip('/')
        inputs.append(s)
        outputs.extend(self._setup_sync(s, d, id or x, m))

    for s in paths:
      assert isinstance(s, str)
      if isinstance(s, pps.path.file.FilePath): #! bad
        s = iprefix / s
      s = P(s)
      inputs.append(s)
      outputs.extend(self._setup_sync(s, dst, id or s, defmode))

    return inputs, outputs

  def _setup_sync(self, sourcefile, dstdir, id, mode):
    if not sourcefile.exists():
      raise IOError("missing input file(s) %s" % sourcefile)
    if dstdir not in self.ptr.diff.handlers['input'].idata:
      self.ptr.diff.handlers['input'].idata.append(sourcefile)

    self.sync_info.setdefault(id, {}).setdefault(sourcefile, set())

    rtn = []
    if sourcefile.isfile():
      output_file = dstdir / sourcefile.basename
      self.sync_info.setdefault(id, {}).setdefault(sourcefile, set()).add((output_file, True, mode))
      self.ptr.diff.handlers['output'].odata.append(output_file)
      rtn.append(output_file)
    else:
      for node in sourcefile.findpaths():
        output_file = dstdir / node.tokens[len(sourcefile.tokens)-1:]
        if node.isfile():
          self.sync_info.setdefault(id, {}).setdefault(node, set()).add((output_file, True, mode))
          self.ptr.diff.handlers['output'].odata.append(output_file)
          rtn.append(output_file)
        else:
          self.sync_info.setdefault(id, {}).setdefault(node, set()).add((output_file, False, mode))
    return rtn

  def sync_input(self, cb=None, link=False, what=None, copy=False):
    """
    Sync the input files to their output locations.

    @param link : if action is not specified, and link is True the
                  input files are linked to the output location.
    @param what : list of IDs identifying what to download.
    """
    if what is None: what = self.sync_info.keys()
    if not hasattr(what, '__iter__'): what = [what]

    sync_items = set()
    chmod_items = set()

    for id in what:
      if not self.sync_info.has_key(id):
        continue
      for src in self.sync_info[id].keys():
        for file, tosync, mode in self.sync_info[id][src]:
          if self.ptr.diff.handlers['input'].diffdict.has_key(src) or not file.exists():
            file.rm(force=True)
            if tosync:
              sync_items.add((src, file))
            if mode:
              chmod_items.add((file, mode))

    outputs = []
    if sync_items:
      sync_items = sorted(sync_items, cmp=lambda x, y: cmp(x[1].basename, y[1].basename))

      cb = cb or self.ptr.files_callback
      cb.sync_start()
      for src, dst in sync_items:
        if copy: self.ptr.copy(src,  dst.dirname, link=link)
        else:    self.ptr.cache(src, dst.dirname, link=link)
        outputs.append(dst)

      for file, mode in chmod_items:
        os.chmod(file, int(mode, 8))

    # if all the files have been sync'd, then remove files that were
    # output files the last time around, but are not output files this
    # time around
    complete = True
    for file in self.list_output():
      if not file.exists():
        # if an output file doesn't exist, it means that it will be sync'd
        # via another sync_input() call in the near-future.
        complete = False
        break
    if complete:
      new_files = set(self.list_output())
      old_files = set()
      for path in self.ptr.diff.handlers['output'].oldoutput.keys():
        for file in path.findpaths(type=TYPE_NOT_DIR):
          old_files.add(file)
      for obsolete_file in old_files.difference(new_files):
        if obsolete_file.exists():
          obsolete_file.rm(force=True)

    return sorted(outputs)

  def clean_eventcache(self, all=False):
    """
    Cleans event cache folder.

    @param all : If all is True, removes all files, else, removes
                 files that are not listed in the output section of
                 the event metadata file.
    """
    if all:
      self.ptr.mddir.listdir(all=True).rm(recursive=True, force=True)
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
        for path in existing.difference(expected):
          path.rm(recursive=True, force=True)
        # remove empty dirs
        dirs = [ d for d in self.ptr.mddir.findpaths(mindepth=1, type=TYPE_DIR) if \
               not d.findpaths(type=TYPE_NOT_DIR) ]
        if not dirs: return
        dirs.reverse()
        for dir in dirs:
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
    rtn = []
    if what is None:
      for path in self.ptr.diff.handlers['output'].odata:
        rtn.extend(path.findpaths(type=TYPE_NOT_DIR))
    else:
      if not hasattr(what, '__iter__'): what = [what]
      for id in what:
        if not self.sync_info.has_key(id):
          continue
        for src in self.sync_info[id].keys():
          for file,_,_ in self.sync_info[id][src]:
            rtn.append(file)
    return sorted(rtn)
