import os
import re
import sys

from centosstudio.util     import shlib
from centosstudio.util     import pps

REGEX_KWPARSE = re.compile('%\(([^\)]+)\).')

def assert_file_has_content(file, cls=None, srcfile=None, **kwargs):
  "Raise a CentOSStudioIOError (or subclass) if a file is not readable or empty."
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
    raise (cls or CentOSStudioIOError)(errno=errno,
                               file=srcfile or file,
                               message=message,
                               **kwargs)

def assert_file_readable(file, cls=None, srcfile=None, **kwargs):
  "Raise a CentOSStudioIOError (or subclass) if a file isn't readable"
  fp = None
  errno = None; message = None
  try:
    try:
      fp = pps.path(file).open()
    except pps.Path.error.PathError, e:
      errno = e.errno; message = os.strerror(e.errno)

    if errno and message:
      raise (cls or CentOSStudioIOError)(errno=errno,
                                 file=(srcfile or file).replace('\n','\\n'),
                                 message=message,
                                 **kwargs)
  finally:
    fp and fp.close()


class CentOSStudioError(Exception): pass

class CentOSStudioEventError(CentOSStudioError):
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


  def __str__(self):
    return self.message % self.map

class CentOSStudioIOError(CentOSStudioEventError, IOError):
  message = "Cannot read file '%(file)s': [errno %(errno)d] %(message)s"

class PpsPathError(CentOSStudioEventError):
  def __str__(self):
    if self.error.errno == 21: # EISDIR
      pass

class ShLibError(CentOSStudioEventError):
  def __init__(self, e):
    self.map = {'cmd': e.cmd, 'errno': e.errno, 'desc': e.desc}
  message = ( "The command '%(cmd)s' exited with an unexepected status code. "
              "Error message was: [errno %(errno)d] %(desc)s" )

class RhnSupportError(RuntimeError, CentOSStudioEventError):
  def __str__(self):
    return ( "RHN support not enabled - please install the 'rhnlib' and "
             "'rhn-client-tools' packages from the centosstudio software repo "
             "at www.centossolutions.com" )

class CentOSStudioEventErrorHandler:
  def _handle_Exception(self, e):
    e = '[%s] %s' % (self.dispatch.currevent.id, handle_Exception(e))
    raise CentOSStudioError(e)


def handle_Exception(e):
  try:
    return ERR_MAP[type(e)](e).__str__()
  except KeyError:
    return e.__str__()

ERR_MAP = {
  shlib.ShExecError:        ShLibError,
 # pps.Path.error.PathError: PpsPathError,
}
