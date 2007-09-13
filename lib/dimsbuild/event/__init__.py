import sys
import traceback

from dims import dispatch
from dims import sync

from diff     import DiffMixin
from fileio   import IOMixin
from validate import ValidateMixin

class Event(dispatch.Event, IOMixin, DiffMixin, ValidateMixin):
  def __init__(self, id, version=0, *args, **kwargs):
    dispatch.Event.__init__(self, id, *args, **kwargs)
    self.event_version = version #!
    self._status = None #!
    
    IOMixin.__init__(self)
    DiffMixin.__init__(self)
    ValidateMixin.__init__(self)
  
  # execution methods
  def run(self):
    ##print 'running %s' % self.id #!
    try:
      self._setup()
      if self.enabled and self._status != False:
        if self._status == True:
          self._clean()
        if self._check():
          self._run()
      self._apply()
    except EventExit, e:
      print e
      sys.exit()
    except Exception, e:
      if hasattr(self, '_error'):
        self._error(e)
      else:
        traceback.print_exc(file=sys.stderr)
      sys.exit(1)
  
  # override these methods to get stuff to actually happen!
  def _add_cli(self, parser): pass
  def _apply_options(self, options): pass
  def _validate(self): pass
  def _setup(self): pass
  def _clean(self): pass
  def _check(self): return True
  def _run(self): pass
  def _apply(self): pass
  
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
  
  def get_mdfile(self):
    file = self.METADATA_DIR/self.id/'%s.md' % self.id
    file.dirname.mkdirs()
    return file

class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)
  
  
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
