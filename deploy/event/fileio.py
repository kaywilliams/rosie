#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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
import errno

from deploy.util import pps
from deploy.util import rxml
from deploy.util import shlib 

from deploy.util.pps.constants import *

from deploy.errors   import DeployEventError

class IOMixin:
  def __init__(self):
    self.io = IOObject(self)

  def clean(self):
    self.io.clean_eventcache(all=True)

  def clean_eventcache(self):
    self.io.clean_eventcache()

  def error(self, e):
    debugdir = self.mddir + '.debug'
    debugdir.rm(recursive=True, force=True)
    self.mddir.rename(debugdir)

  def verify_output_exists(self):
    "all output files exist"
    for file in self.io.list_output():
      self.verifier.failUnlessExists(file)

class IOObject(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.data = {}

    # index for self.data keyed on src/dst
    self.i_src = {}
    self.i_dst = {}

  def abspath(self, f):
    "Transform a path, f, to an absolute path"
    return self.ptr._config.getbase().dirname / f

  def chcon(self, path):
    if self.ptr.cvars['selinux-enabled']:
      shlib.execute('/usr/bin/chcon -R --type=httpd_sys_content_t %s' % path)

  def compute_mode(self, src, mode, content):
    if content == 'text':
      return int((mode or '').lstrip('0') or oct(0644), 8)

    else: #content == 'file'
      return int((mode or '').lstrip('0') or oct((src.stat().st_mode & 07777) or 0644), 8)

  def compute_dst(self, src, dst, content):
    if content == 'text':
      return [(src, dst.normpath())]

    else: # content == 'file'
      r = []
      for s in src.findpaths():
        if not s.isfile(): continue
        r.append((s, (dst/s.relpathfrom(src)).normpath()))
      return r

  def validate_destnames(self, xpaths=None):
    # method called by events to ensure destname is provided for text content;
    # expects a list of path-like elements
    for path in xpaths: #allow python to raise an error of no paths provided
      if path.getxpath('@content', None) and not path.getxpath('@destname',
                                                               None):
        raise InvalidConfigError(message=(
          "Error in file '%s'. Missing 'destname' attribute:\n\n"
                                          "%s" % (path.getbase(), path)))

  def validate_input_file(self, f, allow_text=False, xpath=None):
    # method called by add_item() to ensure the source is a valid file
    if not f: return
    f = self.abspath(f)
    try:
      f.stat()
    except pps.Path.error.PathError, e:
      if isinstance(f, pps.Path.mirror.MirrorPath):
        f = f.touri()        
      if f.exists() and f.islink() and not (f.dirname/f.readlink()).exists():
        raise BrokenLinkError(file=f, target=f.dirname/f.readlink())
      if xpath is not None:
        if allow_text and e.errno == errno.ENOENT: # file not found
          suggest = ("If you are providing text rather than a file, add the "
                     "attribute 'content=\"text\"' to the element.")
        else:
          suggest = ""
        raise XpathInputFileError(message=e, suggest=suggest, 
              elem=str(self.ptr._config.getxpath(xpath)).strip())
      else:
        raise InputFileError(message=e, file=f)

  def add_item(self, src, dst, id=None, mode=None, content='file',
               allow_text=False, xpath=None):
    """
    Adds source/destination pairs to list of possible files to be processed.

    @param src    : the full path, including file basename to a file, or the
                    text of a file to be processed
    @param dst    : the full path, including file basename, of the destination
    @param id     : an identifier for this particular file; need not be unique
    @param mode   : default mode to assign to files
    @param content: content type (file path or text) contained in src parami
    @param xpath  : full xpath to the config element associated with this item
                    (if available)
    """
    if content == 'text':
      # add file content to diff tracking
      if not hasattr(self.ptr, 'file_content'): self.ptr.file_content = {}
      self.ptr.file_content[dst.relpathfrom(self.ptr.mddir)] = src
      self.ptr.diff.variables.vdata.add('file_content[\'%s\']' %
                                         dst.relpathfrom(self.ptr.mddir))

    else: # content == 'file'
      # absolute paths will not be affected by this join
      src = self.abspath(src).normpath()

      # make sure the source file is a valid file
      self.validate_input_file(src, xpath=xpath, allow_text=allow_text)

      self.ptr.diff.input.idata.add(src)

    for s,d in self.compute_dst(src, dst, content):
      m = self.compute_mode(s, mode, content)

      # this should really be in process_items, but it causes problems with
      # test cases - look at again in the future....
      self.ptr.diff.output.odata.add(d)

      td = TransactionData(s,d,m, content, xpath)

      self.data.setdefault(id, set()).add(td)
      # add to indexes as well
      self.i_src.setdefault(s, []).append(td) # one src can go to multiple dsts
      self.i_dst[d] = td # but multiple srcs can't go to one dst

  def add_xpath(self, xpath, dst, id=None, mode=None, destname=None, 
                content='file', allow_text=False, destdir_fallback=None):
    """
    @param xpath : xpath query into the config file that contains zero or
                   more path elements to add to the possible input list
    """
    if not id: id = xpath
    for item in self.ptr.config.xpath(xpath, []):
      # ensure item has text content
      if item.getxpath('text()', None) is None: 
        raise InvalidConfigError(message=("No %s provided for '%s':"
          "\n %s" % (content, 
                     self.ptr._config.getroottree().getpath(item),
                     item)))

      # if item has content...
      s,d,f,m,c = self._process_path_xml(item, destname=destname,
                                         mode=mode, content=content,
                                         destdir_fallback=destdir_fallback)
      item_xpath = self.ptr._config.getroottree().getpath(item)
      self.add_item(s, dst//d/f, id=id, mode=m or mode, content=c, 
                    allow_text=allow_text, xpath=item_xpath )

  def add_xpaths(self, xpaths, *args, **kwargs):
    "Add multiple xpaths at once; calls add_xpath on each element in xpaths"
    if not hasattr(xpaths, '__iter__'): raise TypeError(type(fpaths))
    for xpath in xpaths:
      self.add_xpath(xpath, *args, **kwargs)

  def add_fpath(self, fpath, dst, id=None, mode=None, destname=None):
    """
    @param fpath : file path pointing to an existing file (all pps path
                   types are supported)
    """
    if not id: id = fpath
    fpath = pps.path(fpath)
    self.add_item(fpath, dst//(destname or fpath.basename),
                  id=id, mode=mode, )

  def add_fpaths(self, fpaths, *args, **kwargs):
    "Add multiple fpaths at once; calls add_fpath on each element in fpaths"
    if not hasattr(fpaths, '__iter__'): raise TypeError(type(fpaths))
    for fpath in fpaths:
      self.add_fpath(fpath, *args, **kwargs)

  def process_files(self, callback=None, link=False, cache=False, what=None,
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
      syncfn = self.ptr.cache; cb = callback or self.ptr.cache_callback
    elif link:
      syncfn = self.ptr.link;  cb = callback or self.ptr.link_callback
    else:
      syncfn = self.ptr.copy;  cb = callback or self.ptr.copy_callback

    # add item to transaction if content has changed, or input file has changed,
    # or output file has changed, or output file does not exist; sort on source
    # basename if exists, or output basename.
    tx = sorted([ t for t in self._filter_data(what=what) if
                  (t.xpath and self.ptr.diff.variables.difference(
                               'file_content[\'%s\']' % t.dst.relpathfrom(
                                                        self.ptr.mddir))) or
                  self.ptr.diff.input.difference(t.src) or
                  self.ptr.diff.output.difference(t.dst) or
                  not t.dst.exists() or
                  ( t.dst.exists() and (t.dst.stat().st_mode & 07777) != t.mode)
                  ],
                  key=lambda t: t.sort)

    if tx:
      start_sync = False # only notify callback if have files to sync
      for item in tx:
        if item.content == 'text': # create files from text
          item.dst.dirname.mkdirs()
          item.dst.write_text((item.src + '\n').encode('utf8'))
          item.dst.chmod(item.mode)
        else: # sync existing files
          if start_sync == False:
            cb.sync_start(text=text, count=len(tx))
            start_sync = True
          try:
            syncfn(item.src, item.dst, link=link, mode=item.mode,
                                       callback=cb, **kwargs)
          except pps.Path.error.PathError, e:
            raise InputFileError(message=e, file=item.src)
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
      if self.ptr.mdfile.exists() and self.ptr.diff.output:
        self.ptr.diff.output.clear()

        root = rxml.tree.parse(self.ptr.mdfile).getroot()
        self.ptr.diff.output.mdread(root, self.ptr.mddir)

        expected = set(self.ptr.diff.output.oldoutput.keys())
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
    return sorted(set([ item.dst for item in self._filter_data(what=what) ]))

  def list_input(self, what=None):
    """
    Return a list of input files, or a subset based on ids specified in what
    """
    return sorted([ item.src for item in self._filter_data(what=what) ])

  def _filter_data(self, what=None):
    "process 'what' arguments uniformly"
    if what is None:
      what = self.data.keys()
    elif not hasattr(what, '__iter__'):
      what = [what]

    ret = []
    for id in what:
      for item in self.data.get(id, []):
        ret.append(item)

    return ret

  def _process_path_xml(self, item, destname=None, mode=None, content='file',
                        destdir_fallback=''):
    "compute src, dst, destname, and mode from <path> elements"
    c = item.getxpath('@content', content)
    if c == "file":
      s = self.ptr.config.getpath('%s/text()' % 
                                  self.ptr._config.getroottree().getpath(item))
    else:
      s = item.getxpath('text()')
    d = pps.path(item.getxpath('@destdir', destdir_fallback))
    f = destname or item.getxpath('@destname', None) or s.basename
    m = item.getxpath('@mode', mode)

    return s,d,f,m,c


class TransactionData(object):
  "Simple struct to hold src, dst, mode"
  def __init__(self, src, dst, mode, content, xpath):
    self.src  = src
    self.dst  = dst
    self.mode = mode
    self.content = content
    self.xpath = xpath
    self.sort = ((self.content == 'text' and self.dst.basename) or 
                  self.src.basename)

  def __str__(self):  return str((self.src, self.dst, self.mode, self.content,
                                  self.xpath))
  def __repr__(self): return '%s(%s)' % (self.__class__.__name__, self.__str__())

class InvalidConfigError(DeployEventError):
  message = ("%(message)s")  

class XpathInputFileError(DeployEventError):
  message = ("Error downloading the specified file or folder:\n\n"
             "%(elem)s\n\n"
             "%(suggest)s\n\n"
             "%(message)s.")

class InputFileError(DeployEventError):
  message = ("Error downloading the specified file or folder '%(file)s'.\n\n"
             "%(message)s.")
             
class BrokenLinkError(DeployEventError):
  message = ("Error accessing the file referenced by '%(file)s'. It appears "
             "to be a link to a missing file '%(target)s'.")
