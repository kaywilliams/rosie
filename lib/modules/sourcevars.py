""" 
sourcevars.py

provides information about the source distribution 
"""

__author__  = "Kay Williams <kwilliams@abodiosoftware.com>"
__version__ = "1.0"
__date__    = "June 5th, 2007"

import re
import copy
import os

from os.path  import join, exists
from urlparse import urlparse
from StringIO import StringIO

from dims import FormattedFile as ffile
from dims import osutils
from dims import sync
from dims import imglib
from dims import xmltree
from dims import imerge

from event     import EVENT_TYPE_PROC
from interface import EventInterface
from locals   import LOCALS_XML
from main      import BOOLEANS_TRUE

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'sourcevars',
    'interface': 'SourcevarsInterface',
    'provides': ['ssource-vars'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC
  },
]

HOOK_MAPPING = {
  'SourcevarsHook': 'sourcevars',
}

#------ INTERFACES ------#
class SourcevarsInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  def setSourceVars(self, vars):
    self._base.source_vars = vars

#------ HOOKS ------#
class SourcevarsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sourcevars.sourcevars'
    
    self.interface = interface
    self.vars = self.interface.BASE_VARS

  def run(self):
    #Setup
    i,s,n,d,u,p = self.interface.getStoreInfo(self.interface.getBaseStore())
    d = d.lstrip('/') # un-absolute d
    source_initrd_file = self.interface.storeInfoJoin(s, n, join(d, 'isolinux/initrd.img'))
    cache_initrd_file = join(self.interface.INPUT_STORE, i, d, 'isolinux/initrd.img')

    locals = self.locals_imerge(LOCALS_XML, self.interface.get_cvar('anaconda-version'))

    #Download initrd.img to cache
    osutils.mkdir(osutils.dirname(cache_initrd_file), parent=True)
    sync.sync(source_initrd_file, osutils.dirname(cache_initrd_file), username=u, password=p)

    #Extract buildstamp
    image  = locals.iget('//images/image[@id="initrd.img"]')
    format = image.iget('format/text()')
    zipped = image.iget('zipped/text()', 'False') in BOOLEANS_TRUE
    self.image = imglib.Image(cache_initrd_file, format, zipped)
    self.image.open()
    sourcevars = self.image.read('.buildstamp')

    #Parse buildstamp
    buildstamp_fmt = locals.iget('//buildstamp')
    buildstamp = ffile.XmlToFormattedFile(buildstamp_fmt)
    sourcevars = buildstamp.floread(self.image.read('.buildstamp'))

    #Update source_vars
    #print self.interface.get_cvar('source-vars')
    self.interface.set_cvar('source-vars', sourcevars)
    print self.interface.get_cvar('source-vars')

#------ HELPER FUNCTIONS ------#

  def locals_imerge(self, string, ver):
    tree = xmltree.read(StringIO(string))
    locals = xmltree.Element('locals')
    for child in tree.getroot().getchildren():
      locals.append(imerge.incremental_merge(child, ver))
    return locals
