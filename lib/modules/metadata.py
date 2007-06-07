import copy
import os

from os.path  import join, exists

from dims import filereader
from dims import FormattedFile as ffile
from dims import osutils
from dims import sync

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface
from main      import locals_imerge

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'discinfo',
    'interface': 'MetadataInterface',
    'provides': ['.discinfo', 'source-vars'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR
  },
]

HOOK_MAPPING = {
  'DiscinfoHook': 'discinfo',
}

#------ INTERFACES ------#
class MetadataInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  def setSourceVars(self, vars):
    self._base.source_vars = vars


#------ HOOKS ------#
class DiscinfoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'metadata.discinfo'
    
    self.interface = interface
    
    i,s,n,d,u,p = self.interface.getStoreInfo(self.interface.getBaseStore())
    d = d.lstrip('/') # un-absolute d
    
    # remote, input, local discinfo file locations
    self.r_difile = self.interface.storeInfoJoin(s, n, join(d, '.discinfo'))
    self.i_difile = join(self.interface.INPUT_STORE, i, d, '.discinfo')
    self.m_difile = join(self.interface.METADATA_DIR, '.discinfo')
    self.l_difile = join(self.interface.SOFTWARE_STORE, '.discinfo')
    
    self.username = u
    self.password = p
  
  def force(self):
    osutils.rm(self.l_difile, force=True)
    osutils.rm(self.i_difile, force=True)
  
  def pre(self):
    vars = self.interface.BASE_VARS
    fn = self.interface.config.get('//main/fullname/text()', vars['product'])
    vars.update({'fullname': fn})
  
  def run(self):
    "Get the .discinfo file from the base store"
    osutils.mkdir(osutils.dirname(self.i_difile),  parent=True)
    
    sync.sync(self.r_difile, osutils.dirname(self.i_difile),
              username=self.username, password=self.password)
  
  def apply(self):
    locals = locals_imerge(L_DISCINFO_FORMAT,
                           self.interface.get_cvar('anaconda-version'))
    
    discinfo = ffile.XmlToFormattedFile(locals.iget('discinfo'))
    try:
      base_vars = discinfo.read(self.i_difile)
    except filereader.FileReaderError:
      raise RuntimeError, "Cannot find .discinfo file in input store at '%s'" % self.i_difile
    self.interface.set_cvar('source-vars', copy.copy(base_vars))
    base_vars.update(self.interface.BASE_VARS)
    
    # check if a discinfo already exists; if so, only modify if stuff has changed
    if not exists(self.l_difile) or \
       self._discinfo_changed(discinfo.read(self.l_difile), base_vars):
      discinfo.write(self.l_difile, **base_vars)
      os.chmod(self.l_difile, 0644)
      osutils.cp(self.l_difile, self.m_difile) # copy to metadata folder

  def _discinfo_changed(self, newvars, oldvars):
    for k,v in newvars.items():
      if oldvars[k] != v:
        return True
    return False


#------ LOCALS ------#
L_DISCINFO_FORMAT = ''' 
<locals>
  <!-- .discinfo format entries -->
  <discinfo-entries>
    <discinfo version="0">
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
    </discinfo>
  </discinfo-entries>
</locals>
'''
