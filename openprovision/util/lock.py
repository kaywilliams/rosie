import os
import socket

from openprovision.util import pps

class Lock:
  """Simple locking class.  Not particularly thread safe; intended more for
  use as a global script instance lock than for threading."""

  if os.geteuid() == 0:
    VARRUNDIR = pps.path('/var/run')
  else:
    VARRUNDIR = pps.path('.')

  @property
  def addr(self): return '%s@%s' % (self.pid, self.hostname)

  def __init__(self, path):
    """If path is an absolute path, pid file goes there.  Otherwise, it
    will be placed relative to self.VARRUNDIR."""
    self.pid = os.getpid()
    self.hostname = socket.gethostname()
    self.path = self.VARRUNDIR/path

  def acquire(self):
    "Acquire a lock, returning self if successful, False if failed"
    if self.islocked():
      return False

    try:
      self.path.write_text(self.addr+'\n')
    except Exception, e:
      if self.path.isfile():
        try:
          self.path.unlink()
        except:
          pass
      print e
      raise LockAcquisitionError(self.path, self.pid, self.hostname)

    return self

  def release(self):
    "Release the lock, returning self"
    if self.ownlock():
      try:
        self.path.unlink()
      except:
        raise LockReleaseError(self.path, self.pid, self.hostname)
    return self

  def islocked(self):
    "Return True if we have a lock, False otherwise"
    try:
      pid,host = self._readlock()
      os.kill(pid, 0) # send signal 0 to see if process is alive
      return host == self.hostname
    except:
      return False

  def ownlock(self):
    "Return True if we own the lock"
    return self._readlock() == (self.pid, self.hostname)

  def _readlock(self):
    try:
      fo = self.path.open()
      pid, host = fo.read().strip().split('@')
      fo.close()
      return int(pid), host
    except:
      return (None, None)

  def __del__(self):
    "Clean up locks on exit"
    self.release()


class LockError(OSError):
  def __init__(self, path, pid, hostname=None):
    self.path = path
    self.pid = pid
    self.hostname = hostname or socket.gethostname()
    self.args = [path, pid, hostname]

class LockAcquisitionError(LockError):
  def __str__(self):
    return 'Error acquiring lock \'%s\' for pid %d' % (self.path, self.pid)

class LockReleaseError(OSError):
  def __str__(self):
    return 'Error releasing lock \'%s\' for pid %d' % (self.path, self.pid)
