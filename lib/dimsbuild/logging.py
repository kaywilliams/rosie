# TODO - switch this to use the python logging module
# I tried it once, but its more annoying than it seems.  However,
# it would help out in many issues

import sys
import textwrap
import time

from dims import logger

# format of the various printouts
def LEVEL_0_FORMAT(s): return '%s' % s
def LEVEL_1_FORMAT(s): return ' * %s' % s
def LEVEL_2_FORMAT(s): return '   - %s' % s
def LEVEL_3_FORMAT(s): return '     + %s' % s
def LEVEL_4_FORMAT(s): return '       o %s' % s

# convenience for imports/usage
L0 = LEVEL_0_FORMAT
L1 = LEVEL_1_FORMAT
L2 = LEVEL_2_FORMAT
L3 = LEVEL_3_FORMAT
L4 = LEVEL_4_FORMAT

MSG_MAXWIDTH = 75

class Logger(logger.Logger):
  
  def __init__(self, format='%(message)s', timefmt='%Y-%m-%d %X',
                     fmtvals=None,
                     *args, **kwargs):
    logger.Logger.__init__(self, *args, **kwargs)
    
    self._format = format
    self._timefmt = timefmt
    self._fmtvals = fmtvals or {}
  
  def log(self, level, msg, newline=True, format=None, **kwargs):
    msg = self.format(str(msg), format, **kwargs)
    if newline: msg += '\n'
    self.write(level, msg)
  
  def format(self, msg, format=None, **kwargs):
    d = dict(message=msg, time=time.strftime(self._timefmt), **kwargs)
    d.update(self._fmtvals)
    if format: d['message'] = format % d
    return self._format % d
  
  def test(self, priority):
    if self.threshold is None: return True
    else: return logger.Logger.test(self, priority)


class LogContainer(logger.LogContainer):
  def log(self, priority, message, **kwargs):
    for log_obj in self.list:
      if logger.LogContainer.test(self, priority, message, self.threshold, log_obj):
        log_obj.log(priority, message, **kwargs)
  
  def write(self, priority, message, **kwargs):
    for log_obj in self.list:
      if logger.LogContainer.test(self, priority, message, self.threshold, log_obj):
        log_obj.write(priority, message, **kwargs)


def make_log(threshold, logfile=None):
  container = LogContainer()
  console = Logger(threshold=threshold, file_object=sys.stdout,
                   format='%(message)s')
  container.list.append(console)
  container.console = console
  
  if logfile:
    logfile = Logger(threshold=None, file_object=open(logfile, 'a+'),
                     format='%(time)s: %(message)s')
    container.list.append(logfile)
    container.logfile = logfile
  else:
    container.logfile = None
  
  container.test = console.test
  container.threshold = console.threshold
  
  return container
