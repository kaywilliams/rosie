from centosstudio.util import pps

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
  def __str__(self):
    msg = '\nError(s) while processing XIncludes in "%s"' % self.args[0]
    for err in self.args[1].error_log:
      f = pps.path(err.filename)
      if f.exists():
        msg += '\n %s line %d: %s' % (pps.path(err.filename).relpath(), 
                                 err.line, err.message)
      else:
        pass #avoid confusing error, following error sufficient
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

