import os

from os.path  import join
from StringIO import StringIO

import dims.filereader as filereader
import dims.osutils    as osutils
import dims.shlib      as shlib

from event     import EVENT_TYPE_META
from interface import EventInterface

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'RPMS',
    'provides': ['RPMS'],
    'requires': ['.discinfo'], #!
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_META,
  },
]

STORE_XML = ''' 
<store id="dimsbuild-local">
  <path>file://%s</path>
</store>
'''

#------ MIXINS ------#
class RpmsMixin:
  def __init__(self):
    self.LOCAL_REPO = join(self.getMetadata(), 'localrepo/')
  
  def addRPM(self, path):
    osutils.cp(path, self.LOCAL_REPO)
  
  def createrepo(self):
    pwd = os.getcwd()
    os.chdir(self.LOCAL_REPO)
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)


#------ INTERFACES ------#
class RpmsInterface(EventInterface, RpmsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    RpmsMixin.__init__(self)


#------ HOOK FUNCTIONS ------#
def prestores_hook(interface):
  localrepo = join(interface.getMetadata(), 'localrepo/')
  osutils.mkdir(localrepo)
  interface.add_store(STORE_XML % localrepo)

def postRPMS_hook(interface):
  interface.createrepo()

def postrepogen_hook(interface):
  cfgfile = interface.getFlag('repoconfig')
  if not cfgfile: return  
  
  lines = filereader.read(cfgfile)
  
  lines.append('[dimsbuild-local]')
  lines.append('name = dimsbuild-local')
  lines.append('baseurl = file://%s' % join(interface.getMetadata(), 'localrepo/'))
  
  filereader.write(lines, cfgfile)
