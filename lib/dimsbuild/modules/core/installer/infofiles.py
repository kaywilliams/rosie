""" 
infofiles.py

generates distribution information files: .discinfo, .treeinfo, and .buildstamp 
"""

import copy
import time

from ConfigParser import ConfigParser

from dims import FormattedFile as ffile

from dimsbuild.event   import Event
from dimsbuild.logging import L0

API_VERSION = 5.0
EVENTS = {'installer': ['DiscinfoEvent', 'TreeinfoEvent', 'BuildstampEvent']}

class DiscinfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'discinfo',
      provides = ['.discinfo'],
      requires = ['anaconda-version'],
    )
    
    self.difile = self.SOFTWARE_STORE/'.discinfo'
    
    self.DATA =  {
      'variables': ['cvars[\'base-vars\']',
                    'cvars[\'anaconda-version\']'],
      'output':    [self.difile]
    }
  
  def setup(self):
    self.diff.setup(self.DATA)
  
  def run(self):
    self.log(0, L0("generating .discinfo"))
    
    # create empty .discinfo formatted file object
    discinfo = ffile.DictToFormattedFile(self.locals.discinfo_fmt)
    
    # get product, fullname, and basearch from cvars
    base_vars = copy.deepcopy(self.cvars['base-vars'])
    
    # add timestamp and discs using defaults to match anaconda makestamp.py
    base_vars.update({'timestamp': str(time.time()), 'discs': '1'})
    
    # write .discinfo
    self.difile.dirname.mkdirs()
    discinfo.write(self.difile, **base_vars)
    self.difile.chmod(0644)

    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    if not self.difile.exists():
      raise RuntimeError("Unable to find .discinfo file at '%s'" % self.difile)
    self.diff.write_metadata()


class TreeinfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'treeinfo',
      provides = ['.treeinfo'],
      requires = ['anaconda-version'],
    )
    
    self.tifile = self.SOFTWARE_STORE/'.treeinfo'
    
    self.DATA =  {
      'variables': ['cvars[\'base-vars\']',
                    'cvars[\'product-path\']'],
      'output':    [self.tifile]
    }
    
  def setup(self):
    self.diff.setup(self.DATA)
  
  def run(self):
    self.log(0, L0("generating .treeinfo"))
    treeinfo = ConfigParser()
    
    # generate treeinfo sections
    treeinfo.add_section('general')
    treeinfo.set('general', 'family',     self.product)
    treeinfo.set('general', 'timestamp',  time.time())
    treeinfo.set('general', 'variant',    self.product)
    treeinfo.set('general', 'totaldiscs', '1')
    treeinfo.set('general', 'version',    self.version)
    treeinfo.set('general', 'discnum',    '1')
    treeinfo.set('general', 'packagedir', self.cvars['product-path'])
    treeinfo.set('general', 'arch',       self.basearch)
    
    imgsect = 'images-%s' % self.basearch
    treeinfo.add_section(imgsect)
    treeinfo.set(imgsect, 'kernel',       'images/pxeboot/vmlinux')
    treeinfo.set(imgsect, 'initrd',       'images/pxeboot/initrd.img')
    treeinfo.set(imgsect, 'boot.iso',     'images/boot.ixo')
    treeinfo.set(imgsect, 'diskboot.img', 'images/diskboot.img')
    
    treeinfo.add_section('images-xen')
    treeinfo.set('images-xen', 'kernel', 'images/xen/vmlinuz')
    treeinfo.set('images-xen', 'initrd', 'images/xen/initrd.img')
    
    # write .treeinfo
    self.tifile.dirname.mkdirs()
    if not self.tifile.exists():
      self.tifile.touch()
    tiflo = self.tifile.open('w')
    treeinfo.write(tiflo)
    tiflo.close()
    self.tifile.chmod(0644)
    
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    if not self.tifile.exists():
      raise RuntimeError("Unable to find .treeinfo file at '%s'" % self.tifile)

class BuildstampEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'buildstamp',
      provides = ['buildstamp-file'],
      requires = ['anaconda-version', 'source-vars'],
    )
    
    self.bsfile = self.mddir/'.buildstamp'
    
    self.DATA = {
      'variables': ['cvars[\'base-vars\']',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'source-vars\']'],
      'output':    [self.bsfile],
    }
    
  def setup(self):
    self.diff.setup(self.DATA)
    
  def run(self):
    "Generate a .buildstamp file."
    self.log(0, L0("generating .buildstamp"))
    
    buildstamp = ffile.DictToFormattedFile(self.locals.buildstamp_fmt)
    
    base_vars = copy.deepcopy(self.cvars['source-vars'])
    base_vars.update(self.cvars['base-vars'])
    
    self.bsfile.dirname.mkdirs()
    buildstamp.write(self.bsfile, **base_vars)
    self.bsfile.chmod(0644)
    
    self.diff.write_metadata()
  
  def apply(self):
    if not self.bsfile.exists():
      raise RuntimeError("missing file '%s'" % self.bsfile)
    self.cvars['buildstamp-file'] = self.bsfile
