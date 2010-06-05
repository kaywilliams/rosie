#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import sys
import time

from datetime import timedelta

from solutionstudio.util import dispatch
from solutionstudio.util import rxml
from solutionstudio.util import sync

from solutionstudio.logging import L0, L1

from solutionstudio.event.diff   import DiffMixin
from solutionstudio.event.fileio import IOMixin
from solutionstudio.event.locals import LocalsMixin
from solutionstudio.event.verify import VerifyMixin

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
  def __init__(self, id, version=0, suppress_run_message=False, parentid=None,
                         *args, **kwargs):
    dispatch.Event.__init__(self, id, *args, **kwargs)
    self.event_version = version
    self.suppress_run_message = suppress_run_message
    self.parentid = parentid
    self._status = None

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
    # apply to all children if even has CLASS_META property
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
    self.log(5, L0('*** %s ***' % self.id))
    t_start = time.time()
    try:
      if self.skipped:
        self.setup()
        t_setup = time.time()
        t_run = t_setup
      else:
        if self.forced:
          self.clean()
        self.setup()
        t_setup = time.time()
        if self.check():
          if not self.suppress_run_message:
            self.log(1, L0('%s' % self.id))
          self.run()
          t_run = time.time()
          self.postrun() ## FIXME: this is ugly
        else:
          t_run = t_setup # we didn't run run()
      self.apply()
      t_apply = time.time()
      self.verify()
    except EventExit, e:
      self.log(0, e)
      sys.exit()
    except Exception, e:
      self.error(e)
      raise
    t_end = time.time()

    # log various event timing info to log level 5
    self.log(5, L1("Event timing (%s):" % self.id), newline=False)
    self.logger.write(5, "total: %s "  % timedelta(seconds=int(t_end   - t_start)))
    self.logger.write(5, "setup: %s "  % timedelta(seconds=int(t_setup - t_start)))
    self.logger.write(5, "run: %s "    % timedelta(seconds=int(t_run   - t_setup)))
    self.logger.write(5, "apply: %s\n" % timedelta(seconds=int(t_apply - t_run)))

  # override these methods to get stuff to actually happen!
  def validate(self): pass
  def setup(self): pass
  def clean(self):
    self.log(4, L0("cleaning %s" % self.id))
    IOMixin.clean(self)
    DiffMixin.clean(self)
  #def check(self) defined in mixins
  def run(self): pass
  #def postrun(self) defined in DiffMixin
  def apply(self): pass
  #def error(self, e) defined IOMixin

  def log(self, *args, **kwargs): return self.logger.log(*args, **kwargs)

  def cache(self, src, dst, link=False, force=False, **kwargs):
    self.cache_handler.force = force
    if link: self.cache_handler.cache_copy_handler = self.link_handler
    else:    self.cache_handler.cache_copy_handler = self.copy_handler

    kwargs.setdefault('copy_handler', self.cache_handler)
    kwargs.setdefault('callback',     self.cache_callback)

    self.copy(src, dst, **kwargs)

  def copy(self, src, dst, link=False, updatefn=None, **kwargs):
    kwargs.setdefault('copy_handler', self.copy_handler)
    kwargs.setdefault('callback',     self.copy_callback)

    dst.dirname.mkdirs()
    sync.sync(src, dst, updatefn=updatefn or sync.mirror_updatefn, **kwargs)

  def link(self, src, dst, link=False, updatefn=None, **kwargs):
    kwargs.setdefault('copy_handler', self.link_handler)
    kwargs.setdefault('callback',     self.link_callback) # turn off output

    dst.dirname.mkdirs()
    sync.sync(src, dst, updatefn=updatefn or sync.mirror_updatefn, **kwargs)

  @property
  def mddir(self):
    dir = self.METADATA_DIR/self.id
    dir.mkdirs()
    return dir

  @property
  def mdfile(self):
    return self.mddir/'%s.md' % self.id

  @property
  def OUTPUT_DIR(self):
    dir = self.METADATA_DIR/self.id/'output'
    dir.mkdirs()
    return dir

  @property
  def SOFTWARE_STORE(self):
    dir = self.METADATA_DIR/self.id/'output/os'
    dir.mkdirs()
    return dir

  @property
  def config(self):
    try:
      return self._config.get('/solution/%s' % self.moduleid)
    except rxml.errors.XmlPathError:
      return DummyConfig(self._config)


class EventExit:
  "Error an event can raise in order to exit program execution"

class DummyConfig(object):
  "Dummy config class that matches no xpath queries"
  def __init__(self, config):
    self.config = config # the config object this is based around

  def get(self, paths, fallback=rxml.tree.NoneObject()):
    try:
      return self.xpath(paths)[0]
    except rxml.errors.XmlPathError:
      if not isinstance(fallback, rxml.tree.NoneObject):
        return fallback
      else:
        raise

  def xpath(self, paths, fallback=rxml.tree.NoneObject()):
    if not hasattr(paths, '__iter__'): paths = [paths]
    result = []
    for p in paths:
      if not p.startswith('/'): continue # ignore relative path requests
      result = self.config.xpath(p, fallback=fallback)
      if result: break

    if not result:
      if not isinstance(fallback, rxml.tree.NoneObject):
        return fallback
      else:
        raise rxml.errors.XmlPathError("None of the specified paths %s "
                                       "were found in the config file" % paths)

    return result

  def pathexists(self, path):
    if not path.startswith('/'): return False
    return self.config.pathexists(path)

  def getbool(self, path, fallback=rxml.tree.NoneObject()):
    return rxml.config._make_boolean(self.get(path, fallback))

  def getpath(self, path, fallback=rxml.tree.NoneObject()):
    return rxml.config._make_path(self.get(path, fallback), fallback)

  def getpaths(self, path, fallback=rxml.tree.NoneObject()):
    return [ rxml.config._make_path(x) for x in self.xpath(path, fallback) ]
