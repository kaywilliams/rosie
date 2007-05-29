from dims.osutils import find, mkdir
from event        import EVENT_TYPE_META
from os.path      import exists, join
from rpms.lib     import RpmsInterface

import dims.filereader as filereader

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'RPMS',
    'provides': ['RPMS'],
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
  },
]

MODULES = [
  'config',
  'default_theme',
  'logos',  
  'release',
]

STORE_XML = ''' 
<store id="dimsbuild-local">
  <path>file://%s</path>
</store>
'''

#------ HOOK FUNCTIONS ------#
def prestores_hook(interface):
  localrepo = join(interface.getMetadata(), 'localrepo/')
  mkdir(localrepo)
  interface.add_store(STORE_XML % localrepo)

def postRPMS_hook(interface):
  interface.createrepo()

def postrepogen_hook(interface):
  cfgfile = interface.get_cvar('repoconfig')
  if not cfgfile: return  
  lines = filereader.read(cfgfile)
  lines.append('[dimsbuild-local]')
  lines.append('name = dimsbuild-local')
  lines.append('baseurl = file://%s' % join(interface.getMetadata(), 'localrepo/'))  
  filereader.write(lines, cfgfile)
