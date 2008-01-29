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
      self._process_path(pps.Path(path)/prefix/'core', True, *args, **kwargs)

    # process default-off events
    for path in paths:
      self._process_path(pps.Path(path)/prefix/'extensions', False, *args, **kwargs)

    os.chdir(oldcwd)

    self._resolve_events()
    return self.top

  def _process_path(self, path, default, *args, **kwargs):
    for mod in path.findpaths(nregex='.*/(\..*|.*\.pyc)', mindepth=1):
      modid = mod.basename.replace('.py', '')
      if modid in self.disabled: continue # disabled events
      if not default and modid not in self.enabled: continue # default-off events

      modname = mod.tokens[len(path.tokens):].replace('/', '.').replace('.py', '')
      self._process_module(dispatch.load_modules(modname, path, err=False),
                           path, *args, **kwargs)
