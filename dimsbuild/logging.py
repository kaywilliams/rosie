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
  """
  Logging class used in all dimsbuild output.  Extends the logger.Logger class
  and contains some of the features of the python logging module, particularly
  a simplified implementation of message formatting.  As with normal
  logger.Logger objects, this Logger can be attached to any file or file-like
  object, meaning it can be used to write output to the console (sys.stdout),
  to an open file, or even to a file-like object like a socket.
  
  For more details about logging, including log thresholds, see the
  documentation in logger.py.
  
  Formatting
  Logger supports a simple version of the formatting system included in the
  python's logging module.  Essentially, it makes use of keyed % replacement
  combined with a dictionary of format variables in order to display output.
  Format values can be changed at any time; the output of any subsequent log
  or write call will reflect these changes.  Log message format supports the
  full range of printf formatting characters, like '%(time)5.5s' and the like.
  
  A few format values are reserved - 'message' refers to the original message
  passed to the logger object, while 'time' will display the current time
  in the format specified by Logger._timefmt.  All other format values are
  stored in a class instance Logger._fmtvals, which is a dictionary of the
  format name to the value it should be replaced with.
  """
  def __init__(self, format='%(message)s', timefmt='%Y-%m-%d %X',
                     fmtvals=None,
                     *args, **kwargs):
    """
    format  : The format to use when writing a log message with the log()
              method.  This message must inclue '%(message)s' or some
              derivative in order for the actual message to appear in the log.
              This format supports the full range of printf formatting
              characters.  Each replacement token should contain a key that
              is contained either in Logger._fmtvars or is one of 'message'
              or 'time'.
    timefmt : The strftime-style formatting string to use in '%(time)s' and
              derivative replacements
    fmtvals : A dictionary of format key to replacement value pairs that are
              used when logging messages.  Use of 'message' and 'time' as keys
              is discouraged, as these are reserved by the logger itself;
              behavior is undefined if either key is provided.
    """
    logger.Logger.__init__(self, *args, **kwargs)
    
    self._format = format
    self._timefmt = timefmt
    self._fmtvals = fmtvals or {}
  
  def log(self, level, msg, newline=True, format=None, **kwargs):
    """
    If the logger threshold is at or above the given level, format and write
    the given msg to the logger's file object.
    
    level   : The minimum threshold the logger must have in order for this
              message to be displayed; if the logger's threshold is lower than
              this value, then the message is ignored
    msg     : The message to be writted to the logfile.  This message is
              formatted according to format, below, and the Logger's own format
              before being written
    newline : Whether to automatically append a '\n' character to the end of
              the log message; defaults to True
    format  : An additional level of formatting applied to msg before being
              passed to the logger's primary formatter.  Supports the same
              format characters and key identifiers as Logger's format.  If
              none, no additional formatting is applied.  Defaults to None
    kwargs  : Additional key, value pairs to use with formatting this
              particular log message (these are not added to the Logger's
              _fmtvals dictionary, but merely included in the replacement for
              this one call)
    """
    msg = self.format(str(msg), format, **kwargs)
    if newline: msg += '\n'
    self.write(level, msg)
  
  def format(self, msg, format=None, **kwargs):
    """
    Two-step formatting process that takes a message and applies formatting
    to it.
    
    msg    : the message to be formatted
    format : a preliminary format to be applied to the message prior to the
             Logger's global _format
    kwargs : additional key, value pairs to use with formatting
    """
    d = dict(message=msg, time=time.strftime(self._timefmt), **kwargs)
    d.update(self._fmtvals)
    if format: d['message'] = format % d
    return self._format % d
  
  def test(self, priority):
    "Returns true if a log message would be written at a given priority"
    if self.threshold is None: return True
    else: return logger.Logger.test(self, priority)


class LogContainer(logger.LogContainer):
  """
  Log container class based heavily on logger.LogContainer.  See logger.py for
  details on how log containers function.
  """
  def log(self, priority, message, **kwargs):
    for log_obj in self.list:
      if logger.LogContainer.test(self, priority, message, self.threshold, log_obj):
        log_obj.log(priority, message, **kwargs)
  
  def write(self, priority, message, **kwargs):
    for log_obj in self.list:
      if logger.LogContainer.test(self, priority, message, self.threshold, log_obj):
        log_obj.write(priority, message, **kwargs)


class NullLogger(logger.Logger):
  """
  Dummy log-like object that accepts all log attempts but does not write them
  anywhere.  Used in situations when logging is disabled.
  
  (This same thing could probably be achieved by taking a normal Logger object
  and attaching it to '/dev/null'; however, this is more portable)
  """
  def __init__(self, *args, **kwargs):
    logger.Logger.__init__(self, *args, **kwargs)
    self.file_object = self # tricksy, kind of hackish
  def write(self, *args, **kwargs): pass
  def log(self, *args, **kwargs): pass

def make_log(threshold, logfile=None):
  """
  Create and return a LogContainer object containing two Logger objects, the
  first attached to sys.stdout and the second attached to the logfile given
  in the 'logfile' argument.  If 'logfile' is not given or is otherwise None,
  a NullLogger is used instead.  The logger attached to sys.stdout has the
  given threshold; the logfile logger has no threshold.
  
  threshold : the threshold of the console logger
  logger    : the file name to use for the log; if None, a NullLogger is used
              instead
  """
  container = LogContainer([])
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
    container.logfile = NullLogger()
  
  # make the container behave more like the console logger
  container.test      = console.test
  container.threshold = console.threshold
  
  return container
