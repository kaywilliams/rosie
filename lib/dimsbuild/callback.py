"""
callback.py

Callback classes for dimsbuild
"""

from dims.sync.cache    import CachedSyncCallback
from dims.progressbar   import ProgressBar

from dimsbuild.logging import L1, L2

class FilesCallback:
  def __init__(self, logger, relpath):
    self.logger = logger
    self.relpath = relpath

  def rm_start(self):
    self.logger.log(4, L1("removing files"))

  def rm(self, fn):
    self.logger.log(4, L2(fn.relpathfrom(self.relpath)), format='%(message).75s')

  def rmdir_start(self):
    self.logger.log(4, L1("removing empty directories"))

  def rmdir(self, dn):
    self.logger.log(4, L2(dn.relpathfrom(self.relpath)), format='%(message).75s')

  def sync_start(self):
    self.logger.log(1, L1("downloading input files"))

class BuildSyncCallback(CachedSyncCallback):
  def __init__(self, logger, relpath):
    CachedSyncCallback.__init__(self)
    self.logger = logger
    self.relpath = relpath

    if not self.logger.test(3):
      self.bar._fo = None # turn off progressbar output

  # sync callbacks - kinda hackish
  def start(self, src, dest):
    if self.logger.threshold == 2:
      self.logger.log(2, L2(dest.relpathfrom(self.relpath)/src.basename), format='%(message).75s')
  def cp(self, src, dest): pass
  def sync_update(self, src, dest): pass
  def mkdir(self, src, dest): pass

  def _cache_start(self, size, text):
    CachedSyncCallback._cache_start(self, size, L2(text))

  def _cp_start(self, size, text, seek=0.0):
    CachedSyncCallback._cp_start(self, size=size, text=L2(text), seek=seek)
  
  def _cache_end(self):
    self.bar.update(self.bar.status.size)
    self.bar.finish()
    # if we're at log level 3, write the completed bar to the log file
    if self.logger.test(3):
      self.logger.logfile.log(3, str(self.bar))
    del self.bar

  def _link_xdev(self, src, dst):
    self.logger.log(5, "Attempted invalid cross-device link between '%s' "
                       "and '%s'; copying instead" % (src, dst))


class BuildDepsolveCallback:
  def __init__(self, logger):
    self.logger = logger
    self.loop = 1
    self.count = 0
    self.bar = None
  
  def start(self):
    pass
  
  def tscheck(self, unresolved=0):
    self.count = unresolved
    if self.logger.test(2):
      if self.count == 1: msg = 'loop %d (%d package)'
      else:               msg = 'loop %d (%d packages)'
      self.bar = ProgressBar(size=self.count, title=L2(msg % (self.loop, self.count)),
                             layout='%(title)-28.28s [%(bar)s] %(ratio)9.9s (%(time-elapsed)s)',
                             throttle=10)
      self.bar.start()
  
  def pkgAdded(self, pkgtup=None, state=None):
    if self.logger.test(2):
      self.bar.status.position += 1
  
  def restartLoop(self):
    if self.logger.test(2):
      self.bar.update(self.bar.status.size)
      self.bar.finish() #!
      self.logger.logfile.log(2, str(self.bar))
    self.loop += 1
  
  def end(self):
    self.logger.log(2, 'pkglist resolution complete')
