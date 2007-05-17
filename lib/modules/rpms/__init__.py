from os.path import exists, join

import dims.filereader as filereader

from dims.osutils import find, mkdir

from event import EVENT_TYPE_META

from rpms.lib import RpmsInterface

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'RPMS',
    'provides': ['RPMS'],
    'requires': ['.discinfo'],
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
    'requires': ['stores'],        
  },
]

MODULES = [
  'release',
  'logos',
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
  #pkgs = find(interface.LOCAL_REPO, '*.[Rr][Pp][Mm]',
  #            nregex='.*src.[Rr][Pp][Mm]',prefix=False)
  pkgs = find(interface.LOCAL_REPO, '*.[Rr][Pp][Mm]', prefix=False)
  pkgsfile = join(interface.getMetadata(), 'dimsbuild-local.pkgs')
  if len(pkgs) > 0:
    filereader.write(pkgs, pkgsfile)  

def postrepogen_hook(interface):
  cfgfile = interface.get_cvar('repoconfig')
  if not cfgfile: return  
  
  lines = filereader.read(cfgfile)
  
  lines.append('[dimsbuild-local]')
  lines.append('name = dimsbuild-local')
  lines.append('baseurl = file://%s' % join(interface.getMetadata(), 'localrepo/'))
  
  filereader.write(lines, cfgfile)

