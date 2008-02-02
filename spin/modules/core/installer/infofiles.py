"""
infofiles.py

generates distribution information files: .discinfo, .treeinfo, and .buildstamp
"""

import copy
import time

from ConfigParser import ConfigParser

from rendition import FormattedFile as ffile

from spin.event   import Event

API_VERSION = 5.0
EVENTS = {'installer': ['DiscinfoEvent', 'TreeinfoEvent', 'BuildstampEvent']}

class DiscinfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'discinfo',
      provides = ['.discinfo'],
      requires = ['anaconda-version'],
      version = 1
    )

    self.difile = self.SOFTWARE_STORE/'.discinfo'

    self.DATA =  {
      'variables': ['fullname', 'basearch', 'productpath',
                    'cvars[\'anaconda-version\']'],
      'output':    [self.difile]
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    # create empty .discinfo formatted file object
    discinfo = ffile.DictToFormattedFile(self.locals.discinfo_fmt)

    # get product, fullname, and basearch from cvars
    distro_vars = copy.deepcopy(self.cvars['distro-info'])

    # add timestamp and discs using defaults to match anaconda makestamp.py
    distro_vars.update({'timestamp': str(time.time()), 'discs': '1'})

    # write .discinfo
    self.difile.dirname.mkdirs()
    discinfo.write(self.difile, **distro_vars)
    self.difile.chmod(0644)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

  def verify_discinfo_file_exists(self):
    ".discinfo file exists"
    self.verifier.failUnlessExists(self.difile)


class TreeinfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'treeinfo',
      provides = ['.treeinfo'],
      requires = ['anaconda-version'],
      version = 1,
    )

    self.tifile = self.SOFTWARE_STORE/'.treeinfo'

    self.DATA =  {
      'variables': ['product', 'version', 'productpath', 'basearch'],
      'output':    [self.tifile]
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    treeinfo = ConfigParser()

    # generate treeinfo sections
    treeinfo.add_section('general')
    treeinfo.set('general', 'family',     self.product)
    treeinfo.set('general', 'timestamp',  time.time())
    treeinfo.set('general', 'variant',    self.product)
    treeinfo.set('general', 'totaldiscs', '1')
    treeinfo.set('general', 'version',    self.version)
    treeinfo.set('general', 'discnum',    '1')
    treeinfo.set('general', 'packagedir', self.productpath)
    treeinfo.set('general', 'arch',       self.basearch)

    # this probably needs to be versioned
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

  def verify_treeinfo_file_exists(self):
    ".treeinfo file exists"
    self.verifier.failUnlessExists(self.tifile)


class BuildstampEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'buildstamp',
      version = 1,
      provides = ['buildstamp-file'],
      requires = ['anaconda-version', 'base-info'],
    )

    self.bsfile = self.mddir/'.buildstamp'

    self.DATA = {
      'variables': ['fullname', 'version', 'product', 'basearch', 'webloc',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'base-info\']'],
      'output':    [self.bsfile],
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    "Generate a .buildstamp file."

    buildstamp = ffile.DictToFormattedFile(self.locals.buildstamp_fmt)

    distro_vars = copy.deepcopy(self.cvars['base-info'])
    distro_vars.update(self.cvars['distro-info'])

    self.bsfile.dirname.mkdirs()
    buildstamp.write(self.bsfile, **distro_vars)
    self.bsfile.chmod(0644)

    self.diff.write_metadata()

  def apply(self):
    self.cvars['buildstamp-file'] = self.bsfile

  def verify_buildstamp_file_exists(self):
    ".buildstamp file exists"
    self.verifier.failUnlessExists(self.bsfile)
