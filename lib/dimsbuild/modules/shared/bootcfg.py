from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE

P = pps.Path

class BootConfigMixin(object):
  def __init__(self):
    self.bootconfig = BootConfigDummy(self)

class BootConfigDummy(object):
  def __init__(self, ptr):
    self.ptr = ptr
    self.boot_args = None
  
  def setup(self, defaults=None):
    self.boot_args = self.ptr.config.get('boot-config/append-args/text()', '')
    if defaults and \
       self.ptr.config.get('boot-config/@use-defaults', 'True') in BOOLEANS_TRUE:
      self.boot_args += ' ' + defaults
    if self.ptr.cvars['boot-args']:
      self.boot_args += ' ' + self.cvars['boot-args']
  
  def modify(self, dst):
    if not self.boot_args: return
    
    config = P(self.ptr.config.get('boot-config/file/text()',
               self.ptr.cvars['boot-config-file']))
    lines = config.read_lines()
    _label = False # have we seen a label line yet?
    
    for i in range(0, len(lines)):
      tokens = lines[i].strip().split()
      if not tokens: continue
      if   tokens[0] == 'label': _label = True
      elif tokens[0] == 'append':
        if   not _label: continue
        elif len(tokens) < 2: continue
        elif tokens[1] == '-': continue
        lines[i] = '%s %s' % (lines[i].rstrip(), self.boot_args.strip())
    
    dst.remove()
    dst.write_lines(lines)
