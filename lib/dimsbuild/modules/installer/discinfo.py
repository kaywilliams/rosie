""" 
discinfo.py

generates a .discinfo file
"""

__author__  = 'Kay Williams <kwilliams@abodiosoftware.com>'
__version__ = '1.0'
__date__    = 'June 7th, 2007'

import copy
import os
import time

from os.path      import join, exists
from ConfigParser import ConfigParser

from dims import filereader
from dims import FormattedFile as ffile
from dims import osutils
from dims import sync

from dims.sortlib import dcompare

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import DiffMixin
from dimsbuild.misc      import locals_imerge

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'discinfo',
    'parent': 'INSTALLER',
    'provides': ['.discinfo'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
  {
    'id': 'treeinfo',
    'parent': 'INSTALLER',
    'provides': ['.treeinfo'],
    'requires': ['anaconda-version'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  }
]

HOOK_MAPPING = {
  'DiscinfoHook': 'discinfo',
  'TreeinfoHook': 'treeinfo',
}

#------ HOOKS ------#
class DiscinfoHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.discinfo.discinfo'
    
    self.interface = interface
    self.difile = join(self.interface.SOFTWARE_STORE, '.discinfo')

    self.DATA =  {
      'config': ['/distro/main/fullname/text()'],
      'output': [self.difile]
    }
    mdfile = join(self.interface.METADATA_DIR, 'discinfo.md')
    
    DiffMixin.__init__(self, mdfile, self.DATA)
    
  def force(self):
    osutils.rm(self.difile, force=True)
  
  def pre(self):
    vars = self.interface.BASE_VARS
    fn = self.interface.config.get('//main/fullname/text()', vars['product'])
    vars.update({'fullname': fn})
  
  def check(self):
    return self.test_diffs()
  
  def run(self):
    # setup
    locals = locals_imerge(L_DISCINFO_FORMAT, self.interface.cvars['anaconda-version'])
    
    # create empty .discinfo formatted file object
    discinfo = ffile.XmlToFormattedFile(locals.get('discinfo'))
    
    # get product, fullname, and basearch from interface
    base_vars = self.interface.BASE_VARS
    
    # add timestamp and discs using defaults to match anaconda makestamp.py
    base_vars.update({'timestamp': str(time.time()), 'discs': '1'}) #! do we want to be updating the 'real' base vars?
    
    # write .discinfo
    discinfo.write(self.difile, **base_vars)
    os.chmod(self.difile, 0644)
  
  def apply(self):
    if not exists(self.difile):
      raise RuntimeError, "Unable to find .discinfo file at '%s'" % self.difile
    self.write_metadata()


class TreeinfoHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.discinfo.treeinfo'
    
    self.interface = interface
    self.tifile = join(self.interface.SOFTWARE_STORE, '.treeinfo')

    self.DATA =  {
      'output': [self.tifile]
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'treeinfo.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
    
  def force(self):
    osutils.rm(self.tifile, force=True)
    osutils.rm(self.mdfile, force=True)
  
  def check(self):
    if dcompare(self.interface.cvars['anaconda-version'], '11.2.0.66-1') < 0:
      return False
    return self.test_diffs()
  
  def run(self):
    treeinfo = ConfigParser()
    
    # generate treeinfo sections
    treeinfo.add_section('general')
    treeinfo.set('general', 'family',     self.interface.product)
    treeinfo.set('general', 'timestamp',  time.time())
    treeinfo.set('general', 'variant',    self.interface.product)
    treeinfo.set('general', 'totaldiscs', '1')
    treeinfo.set('general', 'version',    self.interface.version)
    treeinfo.set('general', 'discnum',    '1')
    treeinfo.set('general', 'packagedir', self.interface.cvars['product-path'])
    treeinfo.set('general', 'arch',       self.interface.basearch)
    
    imgsect = 'images-%s' % self.interface.basearch
    treeinfo.add_section(imgsect)
    treeinfo.set(imgsect, 'kernel',       'images/pxeboot/vmlinux')
    treeinfo.set(imgsect, 'initrd',       'images/pxeboot/initrd.img')
    treeinfo.set(imgsect, 'boot.iso',     'images/boot.ixo')
    treeinfo.set(imgsect, 'diskboot.img', 'images/diskboot.img')
    
    treeinfo.add_section('images-xen')
    treeinfo.set('images-xen', 'kernel', 'images/xen/vmlinuz')
    treeinfo.set('images-xen', 'initrd', 'images/xen/initrd.img')
    
    # write .treeinfo
    if not exists(self.tifile):
      os.mknod(self.tifile)
    tiflo = open(self.tifile, 'w')
    treeinfo.write(tiflo)
    tiflo.close()
    os.chmod(self.tifile, 0644)
  
  def apply(self):
    if dcompare(self.interface.cvars['anaconda-version'], '11.2.0.66-1') < 0:
      return
    if not exists(self.tifile):
      raise RuntimeError, "Unable to find .treeinfo file at '%s'" % self.tifile
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
