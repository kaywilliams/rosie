import copy
import os

from os.path  import join, exists

import dims.FormattedFile as ffile
import dims.osutils       as osutils
import dims.sync          as sync

from event     import EVENT_TYPE_PROC
from interface import EventInterface, LocalsMixin
from locals    import L_DISCINFO_PATH, L_DISCINFO

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'discinfo',
    'interface': 'MetadataInterface',
    'provides': ['.discinfo'],
    'requires': ['stores'],
    'properties': EVENT_TYPE_PROC,
  },
]

class MetadataInterface(EventInterface, LocalsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()),
                         self._base.IMPORT_DIRS)
  def setSourceVars(self, vars):
    self._base.source_vars = vars
  
def prediscinfo_hook(interface):
  vars = interface.getBaseVars()
  fn = interface.config.get('//main/fullname/text()', vars['product'])
  vars.update({'fullname': fn})

def discinfo_hook(interface):
  "Get the .discinfo file from the base store"
  i,s,n,d,u,p = interface.getStoreInfo(interface.getBaseStore())
  dest = join(interface.getInputStore(), i, d)
  osutils.mkdir(dest, parent=True)
  
  discinfo_path = interface.getLocalPath(L_DISCINFO_PATH, 'path/text()')
  discinfo_fmt  = interface.getLocalPath(L_DISCINFO, '.')
  
  sync.sync(interface.storeInfoJoin(s, n, join(d, discinfo_path)), dest, username=u, password=p)
  
  discinfo = ffile.XmlToFormattedFile(discinfo_fmt)
  base_vars = discinfo.read(join(dest, discinfo_path))
  interface.setSourceVars(copy.copy(base_vars))
  base_vars.update(interface.getBaseVars())
  
  # check if a discinfo already exists; if so, only modify if stuff has changed
  difile = join(interface.getSoftwareStore(), '.discinfo')
  if not exists(difile) or discinfo_changed(discinfo.read(difile), base_vars):
    discinfo.write(difile, **base_vars)
    os.chmod(difile, 0644)

def discinfo_changed(newvars, oldvars):
  for k,v in newvars.items():
    if oldvars[k] != v:
      return True
  return False
