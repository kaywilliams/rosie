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

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'discinfo',
    'interface': 'MetadataInterface',
    'provides': ['.discinfo'],
    'requires': ['stores'],
    'properties': EVENT_TYPE_PROC,
  },
]

#------ INTERFACES ------#
class MetadataInterface(EventInterface, LocalsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()),
                         self._base.IMPORT_DIRS)
  def setSourceVars(self, vars):
    self._base.source_vars = vars


#------ HOOK FUNCTIONS ------#
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

#------ UTILITY FUNCTIONS ------#
def discinfo_changed(newvars, oldvars):
  for k,v in newvars.items():
    if oldvars[k] != v:
      return True
  return False


#------ LOCALS ------#
L_DISCINFO_PATH_NEW = ''' 
<locals>
  <discinfo-path-entries>
    <discinfo-path version="0">
      <path>.discinfo></path>
    </discinfo-path>
  </discinfo-path-entries>
</discinfo-path>
'''

L_DISCINFO_FORMAT_NEW = ''' 
<locals>
  <discinfo-format-entries>
    <discinfo-format version="0">
      <line id="timestamp" position="0">
        <string-format string="%s">
          <format>
            <item>timestamp</item>
          </format>
        </string-format>
      </line>
      <line id="fullname" position="1">
        <string-format string="%s">
          <format>
            <item>fullname</item>
          </format>
        </string-format>
      </line>
      <line id="basearch" position="2">
        <string-format string="%s">
          <format>
            <item>basearch</item>
          </format>
        </string-format>
      </line>
      <line id="discs" position="3">
        <string-format string="%s">
          <format>
            <item>discs</item>
          </format>
        </string-format>
      </line>
      <line id="base" position="4">
        <string-format string="%s/base">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
      <line id="rpms" position="5">
        <string-format string="%s/RPMS">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
      <line id="pixmaps" position="6">
        <string-format string="%s/pixmaps">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </discinfo-format>
  </discinfo-format-entries>
</locals>
'''
