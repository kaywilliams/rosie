#
# Copyright (c) 2010
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
# TODO - switch this to use the python logging module
# I tried it once, but its more annoying than it seems.  However,
# it would help out in many issues

import sys
import textwrap
import time

from systembuilder.util import logger

# format of the various printouts
FORMAT_L0 = '%s'
FORMAT_L1 = ' * %s'
FORMAT_L2 = '   - %s'
FORMAT_L3 = '     + %s'
FORMAT_L4 = '       o %s'

# and some functions that apply these formats
def L0(s): return FORMAT_L0 % s
def L1(s): return FORMAT_L1 % s
def L2(s): return FORMAT_L2 % s
def L3(s): return FORMAT_L3 % s
def L4(s): return FORMAT_L4 % s

MSG_MAXWIDTH = 75

class Logger(logger.Logger):
  """
  Logging class used in all systembuilder output.  Extends the logger.Logger class
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

  def error(self, message): # for yum compat
    return self.log(0, message)


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
    logfile = Logger(threshold=None, file_object=open(str(logfile), 'a+'),
                     format='%(time)s: %(message)s')
    container.list.append(logfile)
    container.logfile = logfile
  else:
    container.logfile = NullLogger()

  # make the container behave more like the console logger
  container.test      = console.test
  container.threshold = console.threshold

  return container
