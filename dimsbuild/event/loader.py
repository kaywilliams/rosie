import os

from dims import dispatch
from dims import pps

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
      self._process_path(pps.Path(path)/prefix/'core',
                         ptype='default-on', *args, **kwargs)

    # process default-off events
    for path in paths:
      self._process_path(pps.Path(path)/prefix/'extensions',
                         ptype='default-off', *args, **kwargs)

    os.chdir(oldcwd)

    self._resolve_events()
    return self.top

  def _process_path(self, path, ptype, *args, **kwargs):
    for mod in path.findpaths(nregex='.*/(\..*|.*\.pyc)', mindepth=1):
      modid = mod.basename.replace('.py', '')
      if ptype == 'default-on':
        if modid in self.disabled: continue
      elif ptype == 'default-off':
        if modid not in self.enabled: continue
      else: raise ValueError(ptype)
      modname = mod.tokens[len(path.tokens):].replace('/', '.').replace('.py', '')
      self._process_module(dispatch.load_modules(modname, path, err=False),
                           path, *args, **kwargs)
