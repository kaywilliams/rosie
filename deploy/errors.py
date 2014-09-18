import os
import re
import sys
import traceback 

from deploy.util     import shlib
from deploy.util     import pps

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

class MissingIdError(DeployEventError):
  message = ("Validation Error: Missing 'id' attribute while validating "
             "'%(element)s' elements.")

class DuplicateIdsError(DeployEventError):
  message = ("Validation Error: Duplicate ids found while validating "
             "'%(element)s' elements. The duplicate id is '%(id)s'.")

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
