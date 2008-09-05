import os
import re
import sys
import traceback

from rendition import shlib
from rendition import pps

REGEX_KWPARSE = re.compile('%\(([^\)]+)\).')

def assert_file_readable(file, cls=None, srcfile=None, **kwargs):
  "Raise a SpinIOError (or subclass) if a file isn't readable or is empty"
  fp = None
  errno = None; message = None
  try:
    try:
      fp = pps.path(file).open()
    except pps.Path.error.PathError, e:
      errno = e.errno; message = os.strerror(e.errno)
    else:
      if not fp.read(1024):
        errno = -1;    message = "file is empty"

    if errno and message:
      raise (cls or SpinIOError)(errno=errno,
                                 file=srcfile or file,
                                 message=message,
                                 **kwargs)
  finally:
    fp and fp.close()

class SpinError:
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

class SpinIOError(SpinError, IOError):
  message = "Cannot read file '%(file)s': [errno %(errno)d] %(message)s"

class PpsPathError(SpinError):
  def __str__(self):
    if self.error.errno == 21: # EISDIR
      pass

class ShLibError(SpinError):
  def __init__(self, e):
    self.map = {'cmd': e.cmd, 'errno': e.errno, 'desc': e.desc}
  message = ( "The command '%(cmd)s' exited with an unexepected status code. "
              "Error message was: [errno %(errno)d] %(desc)s" )

class RhnSupportError(RuntimeError, SpinError):
  def __str__(self):
    return ( "RHN support not enabled - please install then 'rhnlib' and "
             "'rhn-client-tools' packages from the spin software repo "
             "at www.renditionsoftware.com" )

class SpinErrorHandler:
  def _handle_Exception(self, e):
    traceback.print_exc(file=self.logger.logfile.file_object)
    if self.logger.test(4) or self.debug:
      raise
    else:
      self.logger.write(0, '\n') # start on a new line
      if isinstance(e, KeyboardInterrupt):
        self.logger.log(0, "Spin halted on user input")
      else:
        if not isinstance(e, SpinError) and not isinstance(e, KeyboardInterrupt):
          self.logger.write(0,
            "An unhandled exception has been generated while processing "
            "the '%s' event.  The traceback has been recorded in the log "
            "file.  Please report this error by sending a copy of your log "
            "file, config and appliance definition files, and any other "
            "relevant information to contact@renditionsoftware.com.\n\n"
            "Error message was: "
            % self.dispatch.currevent.id)
        self.logger.log(0, '[%s] %s' % (self.dispatch.currevent.id,
                                        handle_Exception(e)))
    sys.exit(1)

def handle_Exception(e):
  try:
    return ERR_MAP[type(e)](e).__str__()
  except KeyError:
    return e.__str__()

ERR_MAP = {
  shlib.ShExecError:        ShLibError,
 # pps.Path.error.PathError: PpsPathError,
}
