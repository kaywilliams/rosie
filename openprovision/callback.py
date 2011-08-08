#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
callback.py

Callback classes for openprovision

This file contains several 'callback' classes primarily intended for reporting
progress information back to the user.  Many make use of progressbar.py to
display this data in a compact, easy-to-read format.
"""

from openprovision.util.progressbar   import ProgressBar
from openprovision.util.sync.cache    import CachedSyncCallback  as _CachedSyncCallback
from openprovision.util.sync.callback import SyncCallbackMetered as _SyncCallbackMetered

from openprovision.sslogging import L1, L2

# progressbar layouts - see progressbar.py for other tags
LAYOUT_TIMER     = '%(title)-67.67s (%(time-elapsed)s)'
LAYOUT_SYNC      = '%(title)-28.28s [%(bar)s] %(curvalue)9.9sB (%(time-elapsed)s)'
LAYOUT_DEPSOLVE  = '%(title)-28.28s [%(bar)s] %(ratio)10.10s (%(time-elapsed)s)'

class LinkCallback(_SyncCallbackMetered):
  """
  Companion callback class to Event.io.*() methods; this class displays
  messages related to file retrieval and cleanup in the event metadata
  directory.
  """
  def __init__(self, logger, relpath):
    """
    logger  : the logger object to which log messages should be written
    relpath : the relative path from which file display should begin; in most
              cases, this should be set to the event's metadata directory
    """
    self.logger = logger
    self.relpath = relpath

  # fileio methods
  def rm_start(self):
    self.logger.log(4, L1("removing files"))

  def rm(self, fn):
    if fn.isabs():
      fn = fn.relpathfrom(self.relpath)
    self.logger.log(4, L2(fn), format='%(message).75s')

  def rmdir_start(self):
    self.logger.log(4, L1("removing directories"))

  def rmdir(self, dn):
    if dn.isabs():
      dn = dn.relpathfrom(self.relpath)
    self.logger.log(4, L2(dn), format='%(message).75s')

  def sync_start(self, text='downloading files', **kwargs):
    if text:
      self.logger.log(1, L1(text))

  def sync_end(self): pass

  # sync methods, stubbed out since default for link is to display nothing
  def start(      self, *args, **kwargs): pass
  def cp(         self, *args, **kwargs): pass
  def mkdir(      self, *args, **kwargs): pass
  def _cp_start(  self, *args, **kwargs): pass
  def _cp_update( self, *args, **kwargs): pass
  def _cp_end(    self, *args, **kwargs): pass
  def _link_xdev(self, src, dst):
    self.logger.log(5, "Attempted invalid cross-device link between '%s' "
                       "and '%s'; copying instead" % (src, dst))


class SyncCallback(LinkCallback):
  """
  Callback class for all file synchronization operations, including those
  performed by Event.sync() and Event.cache().  To maintain visual consistency,
  this class should also be passed as the 'callback' argument to any sync.sync()
  calls made (though it is suggested that Event.sync() be used instead).

  Identical to sync.callback.SyncCallbackMetered except in the following ways:
   * L2 transformation is applied to the 'text' argument (bar 'title')
   * at log level 1 and below, no output is generated
   * at log level 2, only the L2 transformation of the 'text' argument is
     displayed
   * at log level 3 and above, output is normal
   * attempting to link across devices generates a log message at log level 5
     and above

  See sync/callback.py for documentation on the callback methods themselves.
  """
  def __init__(self, logger, relpath):
    """
    logger  : the logger object to which output should be written
    relpath : the relative path from which file display should begin; in most
              cases, this should be set to the event's metadata directory
    """
    _SyncCallbackMetered.__init__(self, layout=LAYOUT_SYNC)
    self.logger = logger
    self.relpath = relpath

    self.enabled = self.logger.test(3) # turn off progressbars below log level 3

  # sync callbacks - kinda hackish
  def start(self, src, dest):
    if self.logger.threshold == 2:
      self.logger.log(2, L2(dest.relpathfrom(self.relpath)/src.basename), format='%(message).75s')

  def _cp_start(self, size, text, seek=0.0):
    _SyncCallbackMetered._cp_start(self, size=size, text=L2(text), seek=seek)

  def _cp_update(self, amount_read):
    _SyncCallbackMetered._cp_update(self, amount_read)

  def _cp_end(self, amount_read):
    _SyncCallbackMetered._cp_end(self, amount_read)

  def _link_xdev(self, src, dst):
    self.logger.log(5, "Attempted invalid cross-device link between '%s' "
                       "and '%s'; copying instead" % (src, dst))


class CachedSyncCallback(_CachedSyncCallback, SyncCallback):
  """
  Callback class for all cached sync operations (Event.cache()).  To maintain
  visual consistency, this class should be passed as the 'callback' argument
  to any sync.cache.sync() calls made (though it is suggested that Event.cache()
  be used instead).

  As this class extends SyncCallback, above, it differs from the standard
  CachedSyncCallback in the same ways, as described above.

  See sync/cache.py for documentation on the callback methods themselves.
  """
  def __init__(self, logger, relpath):
    """
    logger  : the logger object to which output should be written
    relpath : the relative path from which file display should begin; in most
              casess, this should be set to the event's metadata directory
    """
    _CachedSyncCallback.__init__(self)
    SyncCallback.__init__(self, logger, relpath)

  def _cache_start(self, size, text):
    _CachedSyncCallback._cache_start(self, size, L2(text))

  def _cache_end(self):
    self.bar.update(self.bar.status.size)
    self.bar.finish()
    # if we're at log level 3, write the completed bar to the log file
    if self.logger.test(3):
      self.logger.logfile.log(3, str(self.bar))


class SyncCallbackCompressed(SyncCallback):
  """
  Callback class for file synchronization operations. Differs from SyncCallback,
  which it extends, in that it provides a compressed display - a single progress
  bar.
  """
  def start(self, *args, **kwargs): pass
  def sync_start(self, text='downloading files', count=None):
    """
    At log level 1 and below, do nothing
    At log level 2 and above, create a progress bar and start it.

    count : the 'size' of the progress bar (number of rpms)
    """
    SyncCallback.sync_start(self, text=text, count=count)
    if self.logger.test(2):
      self.bar = ProgressBar(size=count, title=L2(''), layout=LAYOUT_GPG)
      self.bar.start()

  def _cp_start(self, size, text, seek=0.0):
    """
    At log level 1 and below, do nothing
    At log level 2 and above, update the progress bar's title
    """
    if self.logger.test(2):
      self.bar.tags['title'] = L2(text)

  def _cp_update(self, amount_read): pass
  def _cp_end(self, amount_read):
    """
    At log level 1 and below, do nothing
    At log level 2 and above, update the progress bar's position
    """
    if self.logger.test(2):
      self.bar.status.position += 1

  def sync_end(self):
    """
    At log level 1 and below, do nothing
    At log level 2 and above, finish off the progress bar and write it to the
    logfile
    """
    if self.logger.test(2):
      self.bar.tags['title'] = L2('done')
      self.bar.update(self.bar.status.size)
      self.bar.finish()
      self.logger.logfile.log(2, str(self.bar))


class BuildDepsolveCallback(object):
  """
  Callback class for depsolve and depsolve-like operations.  Displays progress
  bars for looped dependency solving operations, such as those that occur in
  pkglist or pkgorder computation.

  Callback methods other than groupAdded are defined by yum; see source code
  for examples of usage.
  """
  def __init__(self, logger):
    """
    logger  : the logger object to which output should be written
    """
    self.logger = logger
    self.loop = 1
    self.count = 0
    self.grpcount = 0 # current group number
    self.grptotal = 0 # total number of groups
    self.bar = None

  def setupStart(self):
    if self.logger.test(2):
      msg = 'reading package metadata'
      self.bar = ProgressBar(title=L1(msg),
                             layout=LAYOUT_TIMER,
                             throttle=10)
      self.bar.start()

  def setupEnd(self):
    if self.logger.test(2):
      self.bar.finish()
      self.logger.logfile.log(2, str(self.bar))
      self.bar = None

  def start(self):
    pass

  def groupAdded(self, desc):
    """
    Method allowing depsolve operations to be separated visually into groups;
    not used in traditional depsolving, but becomes useful for package ordering,
    where multiple depsolves are run against one common package set.

    desc : an identifier or description for the group
    """
    self.loop = 1
    self.count = 0
    self.grpcount += 1
    self.bar = None
    self.logger.log(2, L1('group %d/%d (%s)' % (self.grpcount, self.grptotal, desc)))

  def tscheck(self, unresolved=0):
    self.count = unresolved
    if self.logger.test(2):
      msg = 'loop %d (%d package%s)' % (self.loop, self.count, self.count != 1 and 's' or '')
      self.bar = ProgressBar(size=self.count, title=L2(msg),
                             layout=LAYOUT_DEPSOLVE,
                             throttle=10)
      self.bar.start()

  def pkgAdded(self, pkgtup=None, state=None):
    if self.logger.test(2):
      self.bar.status.position += 1

  def restartLoop(self):
    if self.logger.test(2):
      self.bar.update(self.bar.status.size)
      self.bar.finish()
      self.logger.logfile.log(2, str(self.bar))
    self.loop += 1

  def end(self):
    if self.logger.test(2):
      self.bar.update(self.bar.status.size)
      self.bar.finish()
      self.logger.logfile.log(2, str(self.bar))


class PkglistCallback(BuildDepsolveCallback):
  def __init__(self, logger, reqpkgs=None):
    BuildDepsolveCallback.__init__(self, logger)
    self.reqpkgs = reqpkgs or []
    self.obsoletes = []

  def end(self):
    BuildDepsolveCallback.end(self)
    if self.obsoletes:
      warnings = []
      for o, n in [ (x[0], y[0]) for x, y in self.obsoletes ]:
        if o not in self.reqpkgs:
          # We were smart about getting a newer package for something
          # that is not a required package. We don't want to print any
          # warnings in this case.
          continue
        warnings.append("Warning: No package '%s' found in any of the input repositories. "
          "However, the '%s' package obsoletes '%s'. Replace '%s' with '%s' in your "
          "<packages> section to resolve this warning." % (o, n, o, o, n))
      if warnings:
        self.logger.log(0, '\n'.join(warnings))

  def foundObsolete(self, old, new):
    self.obsoletes.append((old, new))

class TimerCallback(object):
  def __init__(self, logger):
    self.logger = logger
    self.bar = None

  def start(self, message):
    if self.logger.test(2):
      self.bar = ProgressBar(layout=LAYOUT_TIMER, title=L1(message))
      self.bar.start()

  def end(self):
    if self.logger.test(2):
      self.bar.finish()
      self.logger.logfile.log(2, str(self.bar))
      self.bar = None
