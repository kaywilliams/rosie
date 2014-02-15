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
from StringIO import StringIO

from deploy import util
from deploy.util import pps

class XmlError(Exception): pass

class XIncludeError(XmlError):
  def __init__(self, message, elem):
    self.file = elem.base
    self.line = elem.sourceline
    self.elem = elem.tostring(lineno=True, with_tail=False).replace(
                'xmlns:xi="http://www.w3.org/2001/XInclude" ', '')
    self.message = message

  def __str__(self):
    msg = ("Error processing XInclude at line %s in %s. %s:\n\n"
           "%s" % (self.line, self.file, self.message, self.elem))
    return msg

class XIncludeXpathError(XIncludeError):
  def __init__(self, message, elem):
    XIncludeError.__init__(self, message, elem)

  def __str__(self):
    msg = ("Error processing XInclude at line %s in %s. %s in xpointer:\n\n"
           "%s" % (self.line, self.file, self.message, self.elem))
    return msg

class ConfigError(StandardError, XmlError): pass

class XmlPathError(StandardError, XmlError):
  "Exception raised when an invalid path is specified"

class XmlSyntaxError(StandardError, XmlError):
  def __init__(self, file, error):
    self.file = file
    self.error = error

  def __str__(self):
    if hasattr(self.file, 'read'):
      msg = 'Error reading XML string:'
    else:
      msg = 'Error reading "%s":' % self.file
    msg += ' %s' % self.error.msg

    # too bad these other potentially useful data points never seem to get set
    # msg += ' %s' % self.error.lineno
    # msg += ' %s' % self.error.offset
    # msg += ' %s' % self.error.print_file_and_line
    # msg += ' %s' % self.error.text

    lines = []
    if hasattr(self.file, 'getvalue'):
      lines = self.file.getvalue().splitlines()
    if isinstance(self.file, basestring):
      pps.path(self.file)
    if hasattr(self.file, 'read_lines'):
      try:
        lines = self.file.read_lines()
      except:
        pass

    if lines:
      pad = len(str(len(lines)))
      extra = '' 
      for i, line in enumerate(lines):
        extra += '%%s%%%dd:%%s' % pad % (i != 0 and '\n' or '', i+1, line)
      msg = '\n' + extra + '\n\n' + msg
    return msg

class MacroError(XmlError):
  def __init__(self, file, message, elem):
    self.file = pps.path(file)
    self.message = message
    self.elem = elem.tostring(lineno=True, with_tail=False)

  def __str__(self):
    msg = ("\nERROR: Unable to resolve macros in '%s'. %s The unresolved "
           "section is:\n\n%s\n" % (self.file, self.message, self.elem))

    return msg

class MacroDefaultsFileNotProvided(XmlError):
  def __str__(self):
    return "ERROR: Unable to resolve macros. No defaults file specified."

class MacroUnableToCreateFile(pps.Path.error.PathError, XmlError):
  def __init__(self, file, error):
    self.file = file
    self.error = error

  def __str__(self):
    return ("ERROR: An error occurred creating the file '%s' for storing "
            "macro values: \n\n%s" % (self.file, self.error))

class MacroDefaultsFileXmlPathError(XmlPathError):
  def __init__(self, message):
    self.message = message

  def __str__(self):
    return ("ERROR: Unable to resolve macro defaults filename. The error "
            "is:\n\n%s\n" % self.message)

class MacroDefaultsFileNameUnresolved(XmlError):
  def __init__(self, filename):
    self.filename = filename

  def __str__(self):
    return ("ERROR: Unable to resolve macros. The defaults file name '%s' "
            "contains unresolved macro placeholders." % self.filename)

class MacroScriptError(XmlError):
  def __init__(self, file, elem, script_file, error): 
    self.file = file
    self.elem = elem.tostring(lineno=True, with_tail=False)
    self.script_file = script_file
    self.error = error

  def __str__(self):
    return ("\nERROR: Unable to execute macro script in '%s'.\n\n%s\n\n"
            "The script was saved to the file '%s' prior to execution. "
            "During execution, the following error occurred:\n\n%s"
             % (self.file, self.elem, self.script_file, self.error))

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
