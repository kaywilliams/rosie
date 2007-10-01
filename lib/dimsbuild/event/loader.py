import os

from dims import dispatch
from dims import pps

class Loader(dispatch.Loader):
  def __init__(self, *args, **kwargs):
    dispatch.Loader.__init__(self, *args, **kwargs)
    
    self.enabled  = []
    self.disabled = []
    
  def load(self, paths, prefix='', *args, **kwargs):
    oldcwd = os.getcwd()
    
    if not hasattr(paths, '__iter__'): paths = [paths]
    
    # process default-on events
    for path in paths:
      for mod in (pps.Path(path)/prefix/'core').findpaths(
          nregex='.*/(\..*|.*\.pyc)', mindepth=1, maxdepth=1):
        if mod.basename.replace('.py', '') in self.disabled: continue
        modname = mod.tokens[len(path.tokens):].replace('/', '.').replace('.py', '')
        self._process_module(dispatch.load_modules(modname, path, err=False),
                             path, *args, **kwargs)
                   
    # process default-off events
    for path in paths:
      for mod in (pps.Path(path)/prefix/'extensions').findpaths(
          nregex='.*/(\..*|.*\.pyc)', mindepth=1, maxdepth=1):
        if mod.basename.replace('.py', '') not in self.enabled: continue
        modname = mod.tokens[len(path.tokens):].replace('/', '.').replace('.py', '')
        self._process_module(dispatch.load_modules(modname, path, err=False),
                             path, *args, **kwargs)
    
    os.chdir(oldcwd)
    
    self._resolve_events()
    return self.top
