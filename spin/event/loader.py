#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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
import os

from rendition import dispatch
from rendition import pps

class Loader(dispatch.Loader):
  def __init__(self, enabled=None, disabled=None, *args, **kwargs):
    dispatch.Loader.__init__(self, *args, **kwargs)

    self.enabled  = enabled  or []
    self.disabled = disabled or []

  def load(self, paths, prefix='', *args, **kwargs):
    oldcwd = os.getcwd()

    if not hasattr(paths, '__iter__'): paths = [paths]

    # process default-on events
    for path in paths:
      self._process_path(pps.path(path)/prefix/'core', True, *args, **kwargs)

    # process default-off events
    for path in paths:
      self._process_path(pps.path(path)/prefix/'extensions', False, *args, **kwargs)

    os.chdir(oldcwd)

    self._resolve_events()
    return self.top

  def _process_path(self, path, default, *args, **kwargs):
    for mod in path.findpaths(nregex='.*/(\..*|.*\.pyc|.*\.pyo)', mindepth=1):
      modid = mod.basename.replace('.py', '')
      if not default and modid not in self.enabled: continue # default-off events

      modname = mod.splitall()[len(path.splitall()):].replace('/', '.').replace('.py', '')

      # don't load disabled events
      skip = False
      for modtoken in modname.split('.'):
        if modtoken in self.disabled:
          skip = True; break
      if skip: continue

      self._process_module(dispatch.load_modules(modname, path, err=False),
                           path, *args, **kwargs)
