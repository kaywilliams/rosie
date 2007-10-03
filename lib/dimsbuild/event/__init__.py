import errno
import sys
import traceback

from dims import dispatch
from dims import sync

from dimsbuild.logging import L0

from dimsbuild.event.diff   import DiffMixin
from dimsbuild.event.fileio import IOMixin
from dimsbuild.event.locals import LocalsMixin


class Event(dispatch.Event, IOMixin, DiffMixin, LocalsMixin):
  """ 
  The Event superclass also has quite a few attributes set up by main.py
  - these attributes are shared across all Event subclasses, but are
  computed just once.  See make_event_superclass() inside main.py for
  more details.
  """
  def __init__(self, id, version=0, *args, **kwargs):
    dispatch.Event.__init__(self, id, *args, **kwargs)
    self.event_version = version #!
    self._status = None #!
    
    IOMixin.__init__(self)
    DiffMixin.__init__(self)
    LocalsMixin.__init__(self)
    
  status = property(lambda self: self._status,
                    lambda self, status: self._apply_status(status))
  
  def _apply_status(self, status):
    self._status = status
    # apply to all children if even has PROPERTY_META property
    if self.test(dispatch.PROPERTY_META):
      for child in self.get_children():
        if not child.test(dispatch.PROPERTY_PROTECTED):
          child._apply_status(status)
  
  forced  = property(lambda self: self.status == True)
  skipped = property(lambda self: self.status == False)
  
  # execution methods
  def execute(self):
    self.log(4, L0('running %s' % self.id))
    try:
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
      self.log(5, L0('running %s.apply()' % self.id))
      self.apply()
    except EventExit, e:
      self._handle_EventExit(e)
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
  
  # former interface methods
  def log(self, *args, **kwargs): return self.logger.log(*args, **kwargs)
  
  def cache(self, src, dst, link=False, force=False, **kwargs):
    self.cache_handler.force = force
    if link: self.cache_handler.cache_copy_handler = self.link_handler
    else:    self.cache_handler.cache_copy_handler = self.copy_handler
    
    kwargs.setdefault('copy_handler', self.cache_handler)
    kwargs.setdefault('callback', self.cache_callback)
    
    dst.mkdirs()
    sync.sync(src, dst, **kwargs)
  
  def copy(self, src, dst, link=False):
    dst.mkdirs()
    if link: sync.link.sync(src, dst)
    else:    sync.sync(src, dst)
  
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
  
  #------ ERROR HANDLING ------#
  def _handle_EventExit(self, e):
    self.log(0, e)
    sys.exit()
  
  def _handle_Exception(self, e):
    if hasattr(self, 'error'):
      self.error(e)
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


from dimsbuild.main import DEBUG # imported here to avoid circular ref
