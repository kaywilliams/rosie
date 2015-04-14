import atexit
import os
import psutil
import re
import sys
import traceback 

from lxml import etree
from signal import signal, SIGTERM

from deploy.util     import shlib
from deploy.util     import pps

from deploy.util.rxml.tree import XML_NS

REGEX_ID = re.compile('^[a-zA-Z0-9-_]+$')
REGEX_KWPARSE = re.compile('%\(([^\)]+)\).')

def assert_file_has_content(file, cls=None, srcfile=None, **kwargs):
  "Raise a DeployIOError (or subclass) if a file is not readable or empty."
  assert_file_readable(file, cls=cls, srcfile=srcfile, **kwargs)
  fp = None
  errno = None
  message = None
  try:
    fp = pps.path(file).open()
    if not fp.read(1024):
      errno = -1
      message = "file is empty"
  finally:
    fp and fp.close()

  if errno and message:
    raise (cls or DeployIOError)(errno=errno,
                               file=srcfile or file,
                               message=message,
                               **kwargs)

def assert_file_readable(file, cls=None, srcfile=None, **kwargs):
  "Raise a DeployIOError (or subclass) if a file isn't readable"
  fp = None
  errno = None; message = None
  try:
    try:
      fp = pps.path(file).open()
    except pps.Path.error.PathError, e:
      errno = e.errno; message = os.strerror(e.errno)

    if errno and message:
      raise (cls or DeployIOError)(errno=errno,
                                 file=(srcfile or file).replace('\n','\\n'),
                                 message=message,
                                 **kwargs)
  finally:
    fp and fp.close()


class DeployError(Exception): pass

class InvalidOptionError(DeployError):
  def __init__(self, value, name, accepted):
    self.value = value
    self.name = name
    self.accepted = accepted

  def __str__(self):
    return ("An invalid value '%s' was provided as an option '%s' to "
            "Deploy. %s" % 
            (self.value, self.name, self.accepted))

class InvalidConfigError(DeployError):
  def __init__(self, file, name, value, accepted):
    self.file = file
    self.name = name
    self.value = value
    self.accepted = accepted

  def __str__(self):
    return ("Validation of '%s' failed. The 'main/%s' element contains an "
            "invalid value '%s'. %s" %
            (self.file, self.name, self.value, self.accepted))

class InvalidMainConfigPathError(DeployError):
  def __init__(self, tag, file, message, elem):
    self.tag = tag
    self.file = pps.path(file)
    self.message = message
    self.elem = elem

  def __str__(self):
    msg = ("ERROR: Unable to resolve %s in '%s'. %s The invalid section "
           "is:\n\n%s" % (self.tag, self.file, self.message, 
                            self.elem.tostring(lineno=True, with_tail=False)))

    return msg

class DeployEventError(DeployError):
  message = None
  def __init__(self, *args, **kwargs):
    self.map = {}
    if self.message:
      req_arg_i = 0
      req_args = REGEX_KWPARSE.findall(self.message)

      # assign args
      for arg in args:
        self.map[req_args[req_arg_i]] = arg
        req_arg_i += 1

      # assign kwargs
      for k,v in kwargs.items():
        if self.map.has_key(k):
          raise TypeError("__init__() got multiple values for keyword argument '%s'"
                          % k)
        elif k not in req_args:
          raise TypeError("__init__() got an unexpected keyword argument '%s'"
                          % k)
        self.map[k] = v
        req_arg_i += 1

      if req_arg_i != len(set(req_args)):
        raise TypeError("__init__() takes exactly %d arguments (%d given)"
                        % (len(req_args), req_arg_i))

    else:
      self.message = args[0]

  def __str__(self):
    return self.message % self.map

class SimpleDeployEventError(DeployEventError):
  message = "%(message)s\n"

class DeployIOError(DeployEventError, IOError):
  message = "Cannot read file '%(file)s': [errno %(errno)d] %(message)s"

class PpsPathError(DeployEventError):
  def __str__(self):
    if self.error.errno == 21: # EISDIR
      pass

class ShLibError(DeployEventError):
  def __init__(self, e):
    self.map = {'cmd': e.cmd, 'errno': e.errno, 'desc': e.desc}
  message = ( "The command '%(cmd)s' exited with an unexepected status code. "
              "Error message was: [errno %(errno)d] %(desc)s" )

class ConfigError(DeployEventError):
  """Base class for formatting element text in error messages.

  Accepts two arguments:
  * elems - elem or list of elements. Required.
  * full  - whether the error text should contain just the start tag, or the 
            full element content. Defaults to False (start tag only).

  Sets two variables:
  * elems -  list of elements
  * errstr - a string containing text for the elements, grouped by the
             file containing the element
  """

  def __init__(self, elems, full=False):
    if isinstance(elems, etree.ElementBase):
      elems = [ elems ]

    self.elems = elems

    lines = []
    lastbase = None
    for e in elems:
      base = e.getbase()
      if base != lastbase:
        lines.append('')
        lines.append('%s:' % e.getbase())
      e.attrib.pop('{%s}base' % XML_NS, None)

      if full: # full elem
        lines.append(str(e).strip())
      else:
        lines.append(re.match(r'<[^>]+>', str(e).strip()).group())
      
      lastbase = base

    self.errstr = '\n'.join(lines)

class IdError(ConfigError):
  def __init__(self, elems):
    ConfigError.__init__(self, elems)

    self.tagname = self.elems[0].tag
    self.id = self.elems[0].get('id', None)

class MissingIdError(IdError):
  def __init__(self, elems):
    IdError.__init__(self, elems)

  def __str__(self):
    return ("Validation Error: Missing 'id' attribute while validating "
            "'%s' elements:\n%s" % (self.tagname, self.errstr))

class InvalidIdError(IdError):
  def __init__(self, elems):
    IdError.__init__(self, elems)

  def __str__(self):
    return ("Validation Error: Invalid id '%s' found while validating '%s' "
            "elements. Valid characters are a-z, A-Z, 0-9, _ and -:\n%s"
            % (self.id, self.tagname, self.errstr))

class DuplicateIdsError(IdError):
  def __init__(self, elems):
    IdError.__init__(self, elems)

  def __str__(self):
    return ("Validation Error: Duplicate ids '%s' found while validating "
            "'%s' elements:\n%s"
            % (self.id, self.tagname, self.errstr))

def kill_proc_tree():
  parent = psutil.Process(os.getpid())
  for child in parent.get_children(recursive=True):
    child.kill()

class DeployCliErrorHandler:
  def __init__(self, error, callback):
    # ensure subprocesses go away when Python exits
    atexit.register(kill_proc_tree)
    signal(SIGTERM, lambda signum, stack_frame: sys.exit(1))

    # error processing
    if isinstance(error, KeyboardInterrupt):
      msg = "\nDeploy halted on user input\n"
      callback.logger.logfile.file_object.write(msg)
      sys.exit(msg)
    if isinstance(error, DeployError):
      callback.logger.write(0, '\n') # start on a new line
      msg = str(error) + '\n'
      callback.logger.logfile.file_object.write(msg)
      sys.exit(msg)
    if isinstance(error, Exception):
      tb = traceback.format_exc()
      callback.logger.logfile.file_object.write(tb)
      if callback.logger.test(4) or callback.debug:
        sys.exit(tb)
      else:
        callback.logger.write(0, '\n') # start on a new line
        if hasattr(callback.logger.logfile.file_object, 'name'):
          msg = (
            "An unhandled exception has been generated while running "
            "Deploy. The traceback has been recorded in the log "
            "file at '%s'. Please report this error by sending a copy "
            "of your log file, system definition file and any other "
            "relevant information to bugs@deployproject.org\n\n"
            "Error message was: %s\n"
            % (callback.logger.logfile.file_object.name, error))
          callback.logger.logfile.file_object.write(msg)
          sys.exit(msg)
        else:
          msg = (           
            "An unhandled exception has been generated while running "
            "Deploy. Please report this error by sending a copy "
            "of the error message, your system definition file and any other "
            "relevant information to bugs@deployproject.org\n\n"
            "Error message was: %s\n" % tb)
          sys.exit(msg)
    else:
      raise error

class DeployEventErrorHandler:
  def _handle_Exception(self, e, event=''):
    event = event or self.dispatch.currevent.id
    msg = '\n[%s] %s' % (event, handle_Exception(e))
    tb = traceback.format_exc()
    if self.debug:
      msg = tb
    else:
      self.logger.logfile.file_object.write(tb)
    raise DeployError(msg)


def handle_Exception(e):
  try:
    return ERR_MAP[type(e)](e).__str__()
  except KeyError:
    return e.__str__()

ERR_MAP = {
  shlib.ShExecError:        ShLibError,
 # pps.Path.error.PathError: PpsPathError,
}
