import copy
import os

from os.path import join

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
  n,s,d,u,p = interface.getStoreInfo(interface.getBaseStore())
  dest = join(interface.getInputStore(), n, d)
  osutils.mkdir(dest, parent=True)
  
  discinfo_path = interface.getLocalPath(L_DISCINFO_PATH, 'path/text()')
  discinfo_fmt  = interface.getLocalPath(L_DISCINFO, '.')
  
  sync.sync(join(s, d, discinfo_path), dest, username=u, password=p)
  
  discinfo = ffile.XmlToFormattedFile(discinfo_fmt)
  base_vars = discinfo.read(join(dest, discinfo_path))
  interface.setSourceVars(copy.copy(base_vars))
  base_vars.update(interface.getBaseVars())
  discinfo.write(join(interface.getSoftwareStore(), '.discinfo'), **base_vars)
  os.chmod(join(interface.getSoftwareStore(), '.discinfo'), 0644)
