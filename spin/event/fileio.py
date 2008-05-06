#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from rendition import pps
from rendition import xmllib

from rendition.pps.constants import *

P = pps.Path

class IOMixin:
  def __init__(self):
    self.io = IOObject(self)

  def clean(self):
    self.io.clean_eventcache(all=True)

  def error(self, e):
    debugdir = self.mddir + '.debug'
    self.mddir.rename(debugdir)

  def verify_output_exists(self):
    "all output files exist"
    for file in self.io.list_output():
      self.verifier.failUnlessExists(file)

class IOObject(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.data = {}

  def add_item(self, src, dst, id=None, mode=None, prefix=None):
    """
    Add a source, destination pair to the list of possible files to be synced.

    @param src    : the full path, including file basename, of the source
    @param dst    : the full path, including file basename, of the destination
    @param id     : an identifier for this particular file; need not be unique
    @param mode   : default mode to assign to files
    @param prefix : the prefix to be prepended to relative paths
    """
    # absolute paths will not be affected by this join
    src = ((prefix or self.ptr._config.file.dirname) / src).normpath()

    if not src.exists():
      raise IOError("missing input file '%s'" % src)

    if src not in self.ptr.diff.handlers['input'].idata:
      self.ptr.diff.handlers['input'].idata.append(src)

    for s in src.findpaths():
      s = s.normpath()
      if not s.isfile(): continue

      out  = (dst/s.relpathfrom(src)).normpath()
      m = int(mode or oct((s.stat().st_mode & 0777) or 0644), 8)

      if out not in self.ptr.diff.handlers['output'].odata:
        self.ptr.diff.handlers['output'].odata.append(out)

      self.data.setdefault(id, set())
      self.data[id].add(TransactionData(s, out, m))

  def add_xpath(self, xpath, dst, id=None, mode=None, prefix=None):
    """
    @param xpath : xpath query into the config file that contains zero or
                   more path elements to add to the possible input list
    """
    if not id: id = xpath
    for item in self.ptr.config.xpath(xpath, []):
      s,d,f,m = self._process_path_xml(item, mode=mode)

      self.add_item(s, dst//d/f, id=id, mode=m, prefix=prefix)

  def add_xpaths(self, xpaths, *args, **kwargs):
    "Add multiple xpaths at once; calls add_xpath on each element in xpaths"
    if not hasattr(xpaths, '__iter__'): raise TypeError(type(fpaths))
    for xpath in xpaths:
      self.add_xpath(xpath, dst, *args, **kwargs)

  def add_fpath(self, fpath, dst, id=None, mode=None, prefix=None):
    """
    @param fpath : file path pointing to an existing file (all pps path
                   types are supported)
    """
    if not id: id = fpath
    fpath = P(fpath)
    self.add_item(fpath, dst//fpath.basename, id=id, mode=mode, prefix=prefix)

  def add_fpaths(self, fpaths, *args, **kwargs):
    "Add multiple fpaths at once; calls add_fpath on each element in fpaths"
    if not hasattr(fpaths, '__iter__'): raise TypeError(type(fpaths))
    for fpath in fpaths:
      self.add_fpath(fpath, *args, **kwargs)

  def sync_input(self, callback=None, link=False, cache=False, what=None,
                       text='downloading files', **kwargs):
    """
    Sync input files to output locations.

    @param callback : SyncCallback instance to use as callback
    @param link     : link files instead of copying
    @param cache    : cache files to cache directory before copying
    @param what     : list of ids to be copied (see add_item, above)
    @param text     : text to be passed to callback object as the 'header'
    @param kwargs   : extra arguments to be passed to sync
    """
    output = []

    if cache:
      sync = self.ptr.cache;  cb = callback or self.ptr.cache_callback
    elif link:
      sync = self.ptr.link;   cb = callback or self.ptr.link_callback
    else:
      sync = self.ptr.copy;   cb = callback or self.ptr.copy_callback

    # add item to transaction if input or output file has changed, or if
    # output file does not exist; sort on source basename
    tx = sorted([ t for t in self._filter_data(what=what) if
                  t.src in self.ptr.diff.handlers['input'].diffdict or
                  t.dst in self.ptr.diff.handlers['output'].diffdict or
                  not t.dst.exists() ],
                cmp=lambda x,y: cmp(x.src.basename, y.src.basename))

    if tx:
      cb.sync_start(text=text, count=len(tx))
      for item in tx:
        item.dst.rm(recursive=True, force=True)
        sync(item.src, item.dst, link=link, callback=cb, **kwargs)
        item.dst.chmod(item.mode)
        output.append(item.dst)
      cb.sync_end()

    return output

  def clean_eventcache(self, all=False, callback=None):
    """
    Clean event cache folder

    @param all      : if True, entire event metadata folder is removed; else,
                      removes all files in the metadata folder that are not
                      listed as output in the event metadata file
    @param callback : callback class to be used for file removal
    """
    cb = callback or self.ptr.copy_callback

    if all:
      self.ptr.mddir.listdir(all=True).rm(recursive=True)
    else:
      if self.ptr.mdfile.exists() and self.ptr.diff.handlers.has_key('output'):
        self.ptr.diff.handlers['output'].clear()

        root = xmllib.tree.read(self.ptr.mdfile)
        self.ptr.diff.handlers['output'].mdread(root)

        expected = set(self.ptr.diff.handlers['output'].oldoutput.keys())
        expected.add(self.ptr.mdfile)
        existing = set(self.ptr.mddir.findpaths(mindepth=1, type=TYPE_NOT_DIR))

        obsolete = existing.difference(expected)
        if obsolete:
          cb.rm_start()
          for path in obsolete:
            cb.rm(path)
            path.rm(recursive=True)

        dirs = [ d for d in
                 self.ptr.mddir.findpaths(mindepth=1, type=TYPE_DIR)
                 if not d.listdir(all=True) ]
        if dirs:
          cb.rmdir_start()
          for dir in dirs:
            cb.rmdir(dir)
            dir.removedirs()

  def list_output(self, what=None):
    """
    Return a list of output files, or a subset based on the ids specified in what
    """
    return sorted([ item.dst for item in self._filter_data(what=what) ])

  def _filter_data(self, what=None):
    "process 'what' arguments uniformly"
    if what is None:
      what = self.data.keys()
    elif not hasattr(what, '__iter__'):
      what = [what]

    ret = []
    for id in what:
      if not self.data.has_key(id): continue
      for item in self.data[id]: ret.append(item)

    return ret

  def _process_path_xml(self, item, relpath=None, absolute=False, mode=None):
    "compute src, dst, filename, and mode from <path> elements"
    s = P(item.get('text()'))
    d = P(item.get('@dest', ''))
    f = item.get('@filename', s.basename)
    m = item.get('@mode', mode)

    if relpath:
      if absolute: d = relpath / d
      else:        d = relpath // d

    return s,d,f,m


class TransactionData(object):
  "Simple struct to hold src, dst, mode"
  def __init__(self, src, dst, mode):
    self.src  = src
    self.dst  = dst
    self.mode = mode

