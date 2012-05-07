#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
import imp
import sys

from centosstudio.util import graph
from centosstudio.util import pps
from centosstudio.util import resolve
from centosstudio.util import tree

from centosstudio.util.versort import Version

CLASS_DEFAULT = 00
CLASS_META    = 01 # meta-class event

PROTECT_ENABLE  = 010
PROTECT_DISABLE = 020
PROTECT_ALL     = 070

class NoneType: pass

class Event(tree.NodeMixin, graph.DirectedNodeMixin, resolve.Item):
  def __init__(self, id, enabled=True, parent=None, properties=0,
                     provides = None,
                     requires = None,
                     comes_before = None,
                     comes_after  = None,
                     conditionally_requires     = None,
                     conditionally_comes_before = None,
                     conditionally_comes_after  = None,
                     conditional = False):
    self.enabled = enabled
    self.properties = properties

    tree.NodeMixin.__init__(self, parent=parent)
    graph.DirectedNodeMixin.__init__(self)

    resolve.Item.__init__(self, id,
                          provides = provides,
                          requires = requires,
                          comes_before = comes_before,
                          comes_after  = comes_after,
                          conditionally_requires     = conditionally_requires,
                          conditionally_comes_before = conditionally_comes_before,
                          conditionally_comes_after = conditionally_comes_after,
                          conditional = conditional)

  def __iter__(self): return tree.depthfirst(self)
  def __str__(self):  return self.id
  def __repr__(self): return '<dispatch.Event instance id=\'%s\'>' % self.id

  def _getroot(self):
    p = self
    while p.parent:
      p = p.parent
    return p

  def _getdepth(self):
    depth = 0
    p = self
    while p.parent:
      depth += 1
      p = p.parent
    return depth

  depth = property(_getdepth)

  # property testing (via bitmasking)
  def test(self, property): return self.properties & property

  # enable/disable
  def enable(self):
    if self.test(PROTECT_ENABLE): raise EventProtectionError()
    self._set_enable(True)
  def disable(self):
    if self.test(PROTECT_DISABLE): raise EventProtectionError()
    self._set_enable(False)
  def _set_enable(self, status):
    self.enabled = status
    if self.test(CLASS_META):
      for e in self.get_children():
        e._set_enable(status) # unconditionally enable/disable

  # event retrieval
  def get(self, eventid, fallback=NoneType()):
    for e in self:
      if e.id == eventid: return e
    if isinstance(fallback, NoneType):
      raise UnregisteredEventError(eventid)
    return fallback

  # printing
  def pprint(self):
    depth = self.depth
    if depth < 1:
      print self.__str__()
    else:
      print '|  ' * (depth-1) + '|- ' + self.__str__()

  # execution
  def execute(self): print 'running', self.id


class Dispatch:
  def __init__(self, event):
    resolver = resolve.Resolver()
    resolver.add_node(event)
    resolved = resolver.resolve()
    self._remove_conditional(resolved)
    self._order = [ x for x in event ]
    self._top = event # pointer to the top-level event
    self.reset() # sets self.index to -1, self.currevent to None
    self.reversed = False

  def __iter__(self):
    return iter(self._top)

  def reset(self):
    self.index = -1
    self.currevent = None

  # iteration
  def next(self): return self.advance(1)
  def prev(self): return self.advance(-1)
  def advance(self, step=1):
    newindex = self.index + step
    if newindex < 0 or newindex >= len(self._order):
      raise StopIteration
    self.index = newindex
    self.currevent = self._order[self.index]
    return self.currevent

  # misc
  def reverse(self):
    self._order.reverse()
    self.reversed = not self.reversed
    self.reset()

  # printing
  def pprint(self):
    self._process('pprint', until=None)

  # execution
  def execute(self, until=None):
    self._process('execute', until=until)

  def _process(self, fn, until, *args, **kwargs):
    "Call event.<fn>(*args, **kwargs) on each events until <until> is reached"
    while True:
      try:
        self.next()
        if not self.currevent.enabled:
          if self.currevent == until or self.currevent.id == until:
            raise StopIteration
          continue
        getattr(self.currevent, fn)(*args, **kwargs)
        if self.currevent == until or self.currevent.id == until:
          raise StopIteration
      except StopIteration:
        break

  def _remove_conditional(self, resolved):
    # removes events marked as conditional if their provides are not 
    # required by any other event
    for top in resolved:
      all_requires = []
      for requires in [ event.requires for event in top ]:
        all_requires.extend(requires)

      for event in [ event for event in top if event.conditional ]:
        keep = False
        for provides in event.provides:
          if provides in all_requires:
            keep = True

        if keep == False:
          event.disable()

  # event retrieval
  def get(self, eventid, fallback=NoneType()):
    return self._top.get(eventid, fallback)

class Loader:
  def __init__(self, ptr, top=None, api_ver=0, ignore=None):
    self.ptr = ptr
    self.module_map = {} # map of moduleid to events
    self.events  = []
    self.modules = {}
    self.module_info = {} # map of moduleid to module_info; allows modules
                          # to calculate their info based on runtime properties
                          # rather than using module global variables

    self.top = top or Event('ALL')
    self.api_ver = api_ver
    self.ignore = ignore or [] # list of module names to ignore while loading

  def load(self, dirs, prefix='', *args, **kwargs):
    "Find all python modules beneath dirs, load all events defined therein, "
    "and construct an appropriate event tree from them, if possible."
    if isinstance(dirs, basestring): dirs = [dirs]
    for dir in [ pps.path(d)/prefix for d in dirs ]:
      for mod in dir.findpaths(nregex='.*/(\..*|.*\.pyc|.*\.pyo)', mindepth=1):
        modid   = str(mod.basename.splitext()[0])
        modname = mod.relpathfrom(dir).splitext()[0].replace('/', '.')
        if modid in self.ignore: continue
        m = load_modules(modname, dir, err=False)
        if hasattr(m, 'get_module_info'):
          self.modules[modid] = m

    for mod in self.modules.values():
      self._process_module(mod, ptr=self.ptr, *args, **kwargs)

    self._resolve_events()
    return self.top

  def _process_module(self, mod, ptr, *args, **kwargs):
    """Process a module and recursively process all submodules as well.
    Creates an instance of each event in EVENTS dictionary, adds event to
    self.events and module info to self.module_map"""
    if not mod: return

    # get module info 
    if not hasattr(mod, 'get_module_info'):
      raise ImportError("Module '%s' does not have get_module_info method" % \
                      mod.__file__)

    modinfo = mod.get_module_info(ptr, *args, **kwargs)

    check_api_version(mod, modinfo, self.api_ver)
    modname = mod.__name__.split('.')[-1]

    # remove module if disabled
    if not modinfo.get('enabled', True):
      self.modules.pop(modname)
      return

    # process events    
    mod_events = modinfo.get('events', [])
    for event in mod_events:
      getattr(mod, event).moduleid = modname
      e = getattr(mod, event)(ptr, *args, **kwargs)
      if e.enabled:
        self.events.append(e)
        self.module_map.setdefault(modname, []).append(e.id)

    # if we haven't added the module to the module_map, i.e. because none of
    # its events are enabled, remove it from the list of modules
    if modname not in self.module_map: 
      self.modules.pop(modname)

    self.module_info[modname] = modinfo

  def _resolve_events(self):
    "'Stitch' together events into an event tree according to the parent"
    "mapping defined in event.parentid"
    firstunreg = None
    while len(self.events) > 0:
      E = self.events.pop(0)
      try:
        self.top.get(E.parentid).append_child(E)
        firstunreg=None
      except KeyError:
        raise UnregisteredEventError(E.id)
      except UnregisteredEventError:
        if E == firstunreg:
          # parent event does not exist, remove event
          self._remove_event(E.id)
          firstunreg=None
          continue
        self.events.append(E)
        if firstunreg is None: firstunreg = E

  def _remove_event(self, event):
    for key in self.module_map.keys():
      if key == event:
        self.module_map.pop(event)
        self.modules.pop(event)
      elif event in self.module_map[key]:
        self.module_map[key] = self.module_map[key].remove(event)
        if self.module_map[key] is None:
          self.module_map.pop(key)
          self.modules.pop(key)

def load_modules(name, dir, err=True):
  "Recursively load the module with name name located underneath dir"
  # don't reload already-loaded modules
  if name in sys.modules.keys():
    return sys.modules[name]

  dir = pps.path(dir)

  loadname = ''
  for token in name.split('.'):
    if loadname: loadname = '%s.%s' % (loadname, token)
    else: loadname = token
    fp = None
    try:
      fp, p, d = imp.find_module(token, [dir])
      module = imp.load_module(loadname, fp, p, d)
    finally:
      fp and fp.close()
    dir = dir / token

  return module

def check_api_version(module, modinfo, api_ver):
  """
  Examine the module m to ensure that the API it is expecting is provided
  by this Build instance.   A given API version  can support modules with
  the same major version number and any minor version number less than or
  equal to its own.   Thus, for example,  a main.py with API_VERSION  set
  to 3.4 results in the following behavior:
    * 0.0-2.x is rejected
    * 3.0-3.4 is accepted
    * 3.5-X.x is rejected
  where X and x are any positive integers.
  """
  mod_api = Version(str(modinfo.get('api', 0)), delims=['.'])
  max_api = Version(str(api_ver), delims=['.'])
  min_api = Version('%s.%s' % (max_api[0], 0), delims=['.'])

  if mod_api > max_api:
    raise ImportError("Module API version '%s' is greater than the"
                      "supplied API version '%s' in module %s" % \
                      (mod_api, max_api, module.__file__))
  elif mod_api < min_api:
    raise ImportError("Module API version '%s' is less than the"
                      "required API version '%s' in module %s" % \
                      (mAPI, rAPI, module.__file__))

#------ ERRORS ------#
class EventProtectionError(StandardError): pass
class UnregisteredEventError(StandardError): pass
