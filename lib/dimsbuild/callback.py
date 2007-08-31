""" 
callback.py

Callback classes for dimsbuild
"""

from dims.sync.cache    import CachedSyncCallback
from dims.progressbar   import ProgressBar

# format of the various printouts
LEVEL_0_FORMAT = '%s'
LEVEL_1_FORMAT = ' * %s'
LEVEL_2_FORMAT = '   - %s'
LEVEL_3_FORMAT = '     + %s'
LEVEL_4_FORMAT = '       o %s'

LEVEL_OTHER_FORMAT = '%s' # format to use if not one of the above

# adjust these as necessary
LEVEL_MIN = 0
LEVEL_MAX = 4

MSG_MAXWIDTH = 40

class FilesCallback:
  def __init__(self, interface):
    self.interface = interface
  
  def remove_start(self):
    self.interface.log(1, "removing files")
  
  def remove(self, fn):
    self.interface.log(4, fn.basename)
  
  def remove_dir_start(self):
    self.interface.log(1, "removing empty directories")
  
  def remove_dir(self, dn):
    self.interface.log(4, dn.basename)
  
  def sync_file_start(self):
    self.interface.log(1, "downloading input files")

class BuildSyncCallback(CachedSyncCallback):
  def __init__(self, threshold):
    CachedSyncCallback.__init__(self)
    self.logger = BuildLogger(threshold)
  
  # sync callbacks - kinda hackish
  def start(self, src, dest):
    if self.logger.threshold == 2:
      self.logger.log(2, '%s' % src.basename, MSG_MAXWIDTH)
  def cp(self, src, dest): pass
  def sync_update(self, src, dest): pass
  def mkdir(self, src, dest): pass
  
  def _cache_start(self, size, text):
    CachedSyncCallback._cache_start(self, size, LEVEL_2_FORMAT % text)
  
  def _cp_start(self, size, text, seek=0.0):
    CachedSyncCallback._cp_start(self, size=size, text=LEVEL_2_FORMAT % text,
                                       seek=seek, draw=self.logger.test(3))
  
  def _cp_update(self, amount_read):
    CachedSyncCallback._cp_update(self, amount_read=amount_read,
                                        draw=self.logger.test(3))

  def _cp_end(self, amount_read):
    CachedSyncCallback._cp_end(self, amount_read=amount_read,
                                     draw=self.logger.test(3))


class BuildDepsolveCallback:
  def __init__(self, threshold):

    self.logger = BuildLogger(threshold)
    self.loop = 1
    self.count = 0
    self.bar = None
  def pkgAdded(self, pkgtup=None, state=None):
    if self.logger.test(2):
      self.bar.update(self.bar.position+1)
      self.bar.draw()
  def start(self):
    pass
  def tscheck(self, unresolved=0):
    self.count = unresolved
    if self.logger.test(2):
      if self.count == 1: msg = 'loop %d (%d package)'
      else:               msg = 'loop %d (%d packages)'
      self.bar = ProgressBar(self.count, LEVEL_2_FORMAT % (msg % (self.loop, self.count)))
      self.bar.layout = '[title:width=28] [ratio:width=9] [bar] [percent] [time]'
      self.bar.start()
      self.bar.draw()
  def restartLoop(self):
    if self.logger.test(2):
      self.bar.finish()
    self.loop += 1
  def end(self):
    self.logger.log(2, 'pkglist resolution complete')


class BuildLogger:
  def __init__(self, threshold):
    self.threshold = int(threshold)
  
  def __call__(self, *args, **kwargs): return self.log(*args, **kwargs)
  
  def test(self, threshold):
    return threshold <= self.threshold
  
  def write(self, level, msg, width=None):
    """ 
    Raw write msg to stdout (trailing newline not appended).  The level argument
    determines the formatting applied.  If it is between LEVEL_MIN and LEVEL_MAX,
    it is used as the formatting replacement to the appropriate LEVEL_X_FORMAT
    string, above; otherwise, it uses LEVEL_OTHER_FORMAT. If, on the other hand,
    level is None, no formatting is applied.  The width argument determines how
    wide the string is.  If it is None, no adjustments are applied; if it is a
    positive integer, the line is padded or truncated to match the specified width.
    """
  
    if not self.test(level): return
    
    if width is not None:
      if width < 4:
        raise ValueError, "Width must be a positive integer greater than 4 or None"
      diff = len(msg) - width
      if diff > 0:
        msg = msg[:-(diff+4)]
        msg += '... '
      else:
        msg += ' ' * (diff*-1)
    
    if level is None:
      print msg,
    elif level >= LEVEL_MIN and level <= LEVEL_MAX:
      print eval('LEVEL_%d_FORMAT' % level) % msg,
    else:
      print '[DEBUG]:', LEVEL_OTHER_FORMAT % msg,
  
  def log(self, level, msg, maxwidth=None):
    self.write(level, msg, maxwidth)
    if self.test(level): print
