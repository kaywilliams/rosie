class XIncludeError(Exception):
  def __str__(self):
    msg = 'Error while processing XInclude in "%s"' % self.args[0]
    for err in self.args[1].error_log:
      msg += '\n  line %d: %s' % (err.line, err.message)
    return msg

class ConfigError(StandardError): pass

class XmlPathError(StandardError):
  "Exception raised when an invalid path is specified"
class XmlSyntaxError(StandardError):
  def __str__(self):
    msg = 'Error while parsing "%s"' % self.args[0]
    for err in self.args[1].error_log:
      msg += '\n  line %d: %s' % (err.line, err.message)
    return msg
class XIncludeSyntaxError(StandardError):
  def __str__(self):
    msg = 'Error while parsing "%s"' % self.args[0]
    for err in self.args[1].error_log:
      msg += '\n  line %d: %s' % (err.line, err.message)
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

