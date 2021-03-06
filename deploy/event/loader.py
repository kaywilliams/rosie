#
# Copyright (c) 2015
# Deploy Foundation. All rights reserved.
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
from deploy.util import dispatch
from deploy.util import pps

class Loader(dispatch.Loader):
  def __init__(self, ptr, enabled=None, disabled=None, load_extensions=False,
                     *args, **kwargs):
    dispatch.Loader.__init__(self, ptr, *args, **kwargs)

    self.enabled  = enabled  or []
    self.disabled = disabled or []
    # if load_extensions is true, extension modules are loaded even without
    # an associated config section or through being explicitly enabled
    self.load_extensions = load_extensions

  def load(self, paths, prefix='', *args, **kwargs):
    if isinstance(paths, basestring): paths = [paths]
    paths = [ pps.path(p) for p in paths ]

    # process default-on events
    for p in paths:
      self._process_path(p/prefix/'core', True)

    # process default-off events
    for p in paths:
      self._process_path(p/prefix/'extensions', self.load_extensions)

    for mod in self.modules.values():
      self._process_module(mod, ptr = self.ptr, *args, **kwargs)

    self._resolve_events()
    return self.top

  def _process_path(self, path, default):
    for mod in path.findpaths(nregex='.*/(\..*|.*\.pyc|.*\.pyo|Makefile)',
                              mindepth=1):
      modid = str(mod.basename.splitext()[0])
      # only load default-off modules if explicitly enabled
      if not default and modid not in self.enabled: continue

      modname = mod.relpathfrom(path).splitext()[0].replace('/', '.')

      # don't load disabled events
      skip = False
      for modtoken in modname.split('.'):
        if modtoken in self.disabled:
          skip = True; break
      if skip: continue

      m = dispatch.load_modules(modname, path, err=False)
      if hasattr(m, 'get_module_info'):
        self.modules.setdefault(modid, m) # only load if not already loaded
