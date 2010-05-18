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
"""
callback.py - Defines callback objects for use with sync.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '0.8.1'
__date__    = 'August 22nd, 2007'

import sys

from solutionstudio.util.progressbar import ProgressBar

THROTTLE = 10 # update a maximum of 10 times per second

class SyncCallback:
  """
  Base callback class - sync callbacks must implement all the callback methods
  listed below.  Alternately, this class can be subclassed and overridden to
  match specific needs (this method is recommended).
  """
  def __init__(self, verbose=False, fo=None):
    """
    Create a SyncCallback object.  Accepts the following parameters:
     * verbose: whether to print out messages upon synching files; defaults to
                False
     * fo:      a file-like object where log messages are written; defaults to
                sys.stdout
    """
    self.verbose = verbose
    self.fo = fo or sys.stdout

  def log(self, msg):
    "Write msg to self.fo"
    if self.verbose:
      self.fo.write('sync: %s\n' % msg)
      self.fo.flush()

  # callback functions - subclasses will likely override these
  def start(self, src, dst):
    """
    Called by sync() immediately once a sync operation begins
     * src: the source, as passed to sync()
     * dst: the destination, as passed to sync()
    """
    pass

  def mkdir(self, src, dst):
    "Called by sync() upon making a directory"
    self.log("making directory '%s'" % dst)

  def rm(self, dst):
    "Called by sync() upon removing a file from the destination during strict sync"
    self.log("removing file '%s'" % dst)

  def update(self, src, dst):
    "Called by sync() when updating an existing file"
    self.log("updating file '%s'" % dst)

  def cp(self, src, dst):
    "Called by sync when copying a new file"
    self.log("copying '%s' to '%s'" % (src, dst))

  def _cp_start(self, size, text, seek=0.0):
    """
    Called by CopyHandler.copy() before the copy process actually begins
     * size:     the size of the file to be copied
     * text:     the text used to describe the file; usually the file name
     * seek:     the position in the file to start at; defaults to 0.0
    """
    pass
  def _cp_update(self, amount_read):
    """
    Called by CopyHandler.copy() after copying a chunk of data from the
    source to the destionation
     * amount_read: the total amount of the source file that has been read
    """
    pass
  def _cp_end(self, amount_read):
    """
    Called by CopyHandler.copy() after completing the copy process
     * amount_read: the total amount of the source file that has been read; in
                    most cases, this should be equal to the size of the source
                    file
    """
    pass

  def end(self, src, dst):
    "Called by sync() once the sync operation completes"
    pass

class SyncCallbackMetered(SyncCallback):
  "A subclass of SyncCallback that adds progress bar reporting of the copy process"
  def __init__(self, verbose=False,
      layout='%(title)-25.25s [%(bar)s] %(curvalue)5.5sB (%(time-elapsed)s)'):
    SyncCallback.__init__(self, verbose=verbose)

    self.layout = layout
    self.bar = None
    self.enabled = True

  def mkdir(self, src, dst): pass
  def rm(self, dst): pass
  def update(self, src, dst): pass
  def cp(self, src, dst): pass

  def _cp_start(self, size, text, seek=0.0):
    self.bar = ProgressBar(layout=self.layout, title=text, position=seek,
                           size=size, throttle=THROTTLE)
    if not self.enabled: self.bar._fo = None
    self.bar.tags.get('curvalue').update(condense=True, ftype=str)
    self.bar.tags.get('maxvalue').update(condense=True, ftype=str)
    self.bar.start()

  def _cp_update(self, amount_read):
    self.bar.update(amount_read)

  def _cp_end(self, amount_read):
    self.bar.update(self.bar.status.size)
    self.bar.finish()
    del self.bar


class SyncCallbackTracker(SyncCallback):
  """A subclass of SyncCallback that attempts to track the status of each file
  as it is synchronized"""
  def __init__(self, verbose=False):
    SyncCallback.__init__(self, verbose=verbose)
    self.reset() # initialize data structures

  def rm(self, dst):
    SyncCallback.rm(self, dst)
    self.removed.append(dst)

  def update(self, src, dst):
    SyncCallback.update(self, src, dst)
    self.updated.append((src,dst))

  def cp(self, src, dst):
    SyncCallback.cp(self, src, dst)
    self.new.append((src,dst))

  def reset(self):
    self.new = []
    self.updated = []
    self.removed = []
