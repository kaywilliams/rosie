""" 
discinfo.py

generates a .discinfo file
"""

__author__  = "Kay Williams <kwilliams@abodiosoftware.com>"
__version__ = "1.0"
__date__    = "June 7th, 2007"

import copy
import os
import time

from os.path  import join, exists

from dims import filereader
from dims import FormattedFile as ffile
from dims import osutils
from dims import sync

from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface
from main      import locals_imerge
from output    import OutputEventHandler

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'discinfo',
    'interface': 'EventInterface',
    'parent': 'INSTALLER',
    'provides': ['.discinfo'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR
  },
]

HOOK_MAPPING = {
  'DiscinfoHook': 'discinfo',
}

#------ HOOKS ------#
class DiscinfoHook(OutputEventHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'metadata.discinfo'
    
    self.interface = interface
    self.difile = join(self.interface.SOFTWARE_STORE, '.discinfo')

    data =  {
      'config': ['/distro/main/fullname/text()'],
      'output': [self.difile]
    }
    mdfile = join(self.interface.METADATA_DIR, 'discinfo.md')

    OutputEventHandler.__init__(self, self.interface.config, data, mdfile)
    
  def force(self):
    osutils.rm(self.difile, force=True)
  
  def pre(self):
    vars = self.interface.BASE_VARS
    fn = self.interface.config.get('//main/fullname/text()', vars['product'])
    vars.update({'fullname': fn})
  
  def run(self):
    # setup
    locals = locals_imerge(L_DISCINFO_FORMAT, self.interface.get_cvar('anaconda-version'))
    
    if self.test_input_changed():
  		# create empty .discinfo formatted file object
      discinfo = ffile.XmlToFormattedFile(locals.iget('discinfo'))

      # get product, fullname, and basearch from interface
      base_vars = self.interface.BASE_VARS

      # add timestamp and discs using defaults to match anaconda makestamp.py
      ts = "%f" % time.time()
      discs = "1"
      base_vars.update({'timestamp': ts, 'discs': discs})

      # write .discinfo
      discinfo.write(self.difile, **base_vars)
      os.chmod(self.difile, 0644)

      # write metadata
      self.write_metadata()

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
        <string-format string="%s">
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
