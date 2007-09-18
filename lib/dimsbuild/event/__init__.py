import sys
import traceback

from dims import dispatch
from dims import sync

from dimsbuild.event.diff     import DiffMixin
from dimsbuild.event.fileio   import IOMixin
from dimsbuild.event.validate import ValidateMixin

class Event(dispatch.Event, IOMixin, DiffMixin, ValidateMixin):
  def __init__(self, id, version=0, *args, **kwargs):
    dispatch.Event.__init__(self, id, *args, **kwargs)
    self.event_version = version #!
    self._status = None #!
    
    IOMixin.__init__(self)
    DiffMixin.__init__(self)
    ValidateMixin.__init__(self)
  
  # execution methods
  def execute(self):
    ##print 'running %s' % self.id #!
    try:
      self.setup()
      if self.enabled and self._status != False:
        if self._status == True:
          self.clean()
        if self.check():
          self.run()
      self.apply()
    except EventExit, e:
      print e
      sys.exit()
    except Exception, e:
      if hasattr(self, 'error'):
        self.error(e)
      ##else:
      traceback.print_exc(file=sys.stderr) #!
      sys.exit(1)
  
  # override these methods to get stuff to actually happen!
  def _add_cli(self, parser): pass
  def _apply_options(self, options): pass
  def validate(self): pass
  def setup(self): pass
  def clean(self):
    self.log(0, "cleaning %s" % self.id)
    IOMixin.clean(self)
    DiffMixin.clean(self)
  #def check(self) defined in mixins
  def run(self): pass
  def apply(self): pass
  
  # former interface methods
  def log(self, level, msg):    self.logger.log(level, msg)
  def errlog(self, level, msg): self.errlogger.log(level, msg)
  
  def cache(self, src, dst, link=False, force=False, **kwargs):
    self.cache_handler.force = force
    if link: self.cache_handler.cache_copy_handler = self.link_handler
    else:    self.cache_handler.cache_copy_handler = self.copy_handler
    
    if not kwargs.has_key('copy_handler'):
      kwargs['copy_handler'] = self.cache_handler
    if not kwargs.has_key('callback'):
      kwargs['callback'] = self.cache_callback
    
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
  

class RepoMixin:
  # TODO examine possiblity of defining this in SOFTWARE meta #!
  def getBaseRepoId(self):
    return self.config.get('/distro/repos/repo[@type="base"]/@id')
  def getAllRepos(self):
    return self.cvars['repos'].values()
  def getRepo(self, repoid):
    return self.cvars['repos'][repoid]


class EventExit:
  "Error an event can raise in order to exit program execution"
