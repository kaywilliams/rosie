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
from deploy import util
from deploy.util import pps

class XmlError(Exception): pass

class XIncludeError(XmlError):
  def __str__(self):
    msg = 'Error while processing XInclude in "%s"' % self.args[0]
    for err in self.args[1].error_log:
      msg += '\n  line %d: %s' % (err.line, err.message)
    return msg

class ConfigError(StandardError, XmlError): pass

class XmlPathError(StandardError, XmlError):
  "Exception raised when an invalid path is specified"

class XmlSyntaxError(StandardError, XmlError):
  def __str__(self):
    msg = '\nError(s) while reading "%s"' % self.args[0]
    for err in self.args[1].error_log:
      msg += '\n  line %d: %s' % (err.line, err.message)
    return msg

class XIncludeSyntaxError(StandardError, XmlError):
  def __init__(self, file, error, submessage='', invalid=''):
    self.file = file
    self.error = error
    self.invalid = invalid
    self.submessage = submessage

  def __str__(self):
    msg = '\nError(s) while processing XIncludes in "%s":' % self.file
    if self.submessage:
      msg.replace(':', '.')
      msg += " %s:\n" % self.submessage.rstrip('.')
    for err in self.error.error_log:
      message = err.message
      if err.filename != "<string>":
        msg += ('\n%s line %d: %s' %
               (pps.path(err.filename), err.line, message))
      else:
        msg += '\nline %d: %s' % (err.line, message)
      if self.invalid:
        msg += '\n\nThe invalid section is:\n'
        msg += self.invalid 
    return msg

class MacroError(XmlError):
  def __init__(self, file, message, elem):
    self.file = file
    self.message = message
    self.elem = elem

  def __str__(self):
    msg = ("\nError resolving macros in '%s'. %s The invalid section is:"
           "\n\n%s\n" % (self.file, self.message, self.elem))

    return msg


#-----------ERROR HELPERS---------#
class ErrorLog(object):
  def __init__(self, logs=None):
    self.error_log = []
    if logs:
      for log in logs:
        self.add(log)
  def add(self, log):
    self.error_log.append(log)
class LogEntry(object):
  def __init__(self, line, message):
    self.line = line
    self.message = message

