import errno
import sys
import traceback

from dims import dispatch
from dims import sync
from dims.xmllib import tree

from dimsbuild.logging import L0, L1

from dimsbuild.event.diff   import DiffMixin
from dimsbuild.event.fileio import IOMixin
from dimsbuild.event.locals import LocalsMixin
from dimsbuild.event.verify import VerifyMixin

# Constant (re)definitions
CLASS_DEFAULT = dispatch.CLASS_DEFAULT
CLASS_META    = dispatch.CLASS_META

PROTECT_ENABLE  = dispatch.PROTECT_ENABLE
PROTECT_DISABLE = dispatch.PROTECT_DISABLE
PROTECT_SKIP    = 0100
PROTECT_FORCE   = 0200
PROTECT_STATUS  = 0700 # protect all changes to Event.status
PROTECT_ENABLED = 0070 # protect all changes to Event.enabled
PROTECT_ALL     = PROTECT_STATUS | PROTECT_ENABLED

STATUS_FORCE = True
STATUS_SKIP  = False


class Event(dispatch.Event, IOMixin, DiffMixin, LocalsMixin, VerifyMixin):
  """
  The Event superclass also has quite a few attributes set up by main.py
  - these attributes are shared across all Event subclasses, but are
  computed just once.  See make_event_superclass() inside main.py for
  more details.
  """
  def __init__(self, id, version=0, *args, **kwargs):
    dispatch.Event.__init__(self, id, *args, **kwargs)
    self.event_version = version
    self._status = None
    self._run = False # indicates when run() is called #! hack for testing?

    IOMixin.__init__(self)
    DiffMixin.__init__(self)
    LocalsMixin.__init__(self)
    VerifyMixin.__init__(self)

  status = property(lambda self: self._status,
                    lambda self, status: self._apply_status(status))

  def _apply_status(self, status):
    if not self._check_status(status):
      raise dispatch.EventProtectionError()
    self._status = status
    # apply to all children if event has CLASS_META property
    if self.test(CLASS_META):
      for child in self.get_children():
        if child._check_status(status):
          child._apply_status(status)

  def _check_status(self, status):
    "Returns True if status change is ok; False if invalid"
    return (status == STATUS_FORCE and not self.test(PROTECT_FORCE)) or \
           (status == STATUS_SKIP  and not self.test(PROTECT_SKIP)) or \
           (status is None)

  forced  = property(lambda self: self.status == STATUS_FORCE)
  skipped = property(lambda self: self.status == STATUS_SKIP)

  # execution methods
  def execute(self):
    self.log(1, L0('%s' % self.id))
    try:
      if (self.mddir/'debug').exists():
        self.log(5, L0('removing %s/debug folder' % self.mddir))
        (self.mddir/'debug').rm(recursive=True, force=True)
      self.log(5, L0('running %s.setup()' % self.id))
      self.setup()
      if not self.skipped:
        if self.forced:
          self.log(5, L0('running %s.clean()' % self.id))
          self.clean()
        self.log(5, L0('running %s.check()' % self.id))
        if self.check():
          self.log(5, L0('running %s.run()' % self.id))
          self.run()
          self._run = True #!
      self.log(5, L0('running %s.apply()' % self.id))
      self.apply()
      self.log(5, L0('running %s.verify()' % self.id))
      self.verify()
    except EventExit, e:
      self._handle_EventExit(e)
    except KeyboardInterrupt, e:
      self._handle_KeyboardInterrupt(e)
    except Exception, e:
      self._handle_Exception(e)

  # override these methods to get stuff to actually happen!
  def _add_cli(self, parser): pass
  def _apply_options(self, options): pass
  def validate(self): pass
  def setup(self): pass
  def clean(self):
    self.log(4, L0("cleaning %s" % self.id))
    IOMixin.clean(self)
    DiffMixin.clean(self)
  #def check(self) defined in mixins
  def run(self): pass
  def apply(self): pass
  #def error(self, e) defined IOMixins

  # former interface methods
  def log(self, *args, **kwargs): return self.logger.log(*args, **kwargs)

  def cache(self, src, dst, link=False, force=False, **kwargs):
    self.cache_handler.force = force
    if link: self.cache_handler.cache_copy_handler = self.link_handler
    else:    self.cache_handler.cache_copy_handler = self.copy_handler

    kwargs.setdefault('copy_handler', self.cache_handler)
    kwargs.setdefault('callback', self.cache_callback)

    self.copy(src, dst, **kwargs)

  def copy(self, src, dst, **kwargs):
    kwargs.setdefault('copy_handler', self.copy_handler)
    kwargs.setdefault('callback', self.copy_callback)

    dst.mkdirs()
    sync.sync(src, dst, **kwargs)

  def link(self, src, dst, **kwargs):
    kwargs.setdefault('copy_handler', self.link_handler)
    kwargs.setdefault('callback', self.link_callback) # turn off output

    dst.mkdirs()
    sync.sync(src, dst, **kwargs)

  def _get_mddir(self):
    dir = self.METADATA_DIR/self.id
    dir.mkdirs()
    return dir
  mddir = property(_get_mddir)

  def _get_mdfile(self):
    return self.mddir/'%s.md' % self.id
  mdfile = property(_get_mdfile)

  def _get_output_dir(self):
    dir = self.METADATA_DIR/self.id/'output'
    dir.mkdirs()
    return dir
  OUTPUT_DIR = property(_get_output_dir)

  def _get_software_store(self):
    dir = self.METADATA_DIR/self.id/'output/os'
    dir.mkdirs()
    return dir
  SOFTWARE_STORE = property(_get_software_store)

  def _get_config(self):
    try:
      return self._config.get('/distro/%s' % self.__module__.split('.')[-1])
    except tree.XmlPathError:
      return DummyConfig(self._config)
  config = property(_get_config)

  #------ ERROR HANDLING ------#
  def _handle_EventExit(self, e):
    self.log(0, e)
    sys.exit()

  def _handle_KeyboardInterrupt(self, e):
    self.error(e)
    raise KeyboardInterrupt

  def _handle_Exception(self, e):
    self.error(e)
    if self.logger.logfile:
      traceback.print_exc(file=self.logger.logfile.file_object)
    if self.logger.test(3) or DEBUG:
      traceback.print_exc(file=self.logger.console.file_object)
    else:
      self.log(0,
        "An unhandled exception has been generated while processing "
        "the '%s' event.  The traceback has been recorded in the log "
        "file.  Please report this error by sending a copy of your "
        "log file, configuration files, and any other relevant "
        "information to contact@abodiosoftware.com.\n\nError message "
        "was: %s" % (self.id, e))
    sys.exit(1)


class EventExit:
  "Error an event can raise in order to exit program execution"

class DummyConfig(object):
  "Dummy config class that matches no xpath queries"
  def __init__(self, config):
    self.config = config # the config object this is based around

  def get(self, paths, fallback=tree.NoneObject()):
    try:
      return self.xpath(paths)[0]
    except tree.XmlPathError:
      if not isinstance(fallback, tree.NoneObject):
        return fallback
      else:
        raise

  def xpath(self, paths, fallback=tree.NoneObject()):
    if not hasattr(paths, '__iter__'): paths = [paths]
    result = []
    for p in paths:
      if not p.startswith('/'): continue # ignore relative path requests
      result = self.config.xpath(p, fallback=fallback)
      if result: break

    if not result:
      if not isinstance(fallback, tree.NoneObject):
        return fallback
      else:
        raise tree.XmlPathError("None of the specified paths %s "
                                "were found in the config file" % paths)

    return result

  def pathexists(self, path):
    if not path.startswith('/'): return False
    return self.config.pathexists(path)


from dimsbuild.main import DEBUG # imported here to avoid circular ref
