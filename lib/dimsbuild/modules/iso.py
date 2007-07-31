import csv
import os

from os.path import join, exists

from dims import filereader
from dims import pkgorder
from dims import listcompare
from dims import osutils
from dims import shlib

from dimsbuild import splittree

from dimsbuild.callback  import BuildDepsolveCallback
from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import DiffMixin, EventInterface, ListCompareMixin
from dimsbuild.misc      import locals_imerge

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'manifest',
    'provides': ['do-iso'],
    'conditional-requires': ['MAIN'],
    'parent': 'ALL',
  },
  {
    'id': 'iso',
    'interface': 'IsoInterface',
    'properties': EVENT_TYPE_MDLR|EVENT_TYPE_PROC,
    'requires': ['anaconda-version'],
    'conditional-requires': ['do-iso', 'source'],
    'parent': 'ALL',
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
  'ManifestHook': 'manifest',
  'IsoHook':      'iso',
  'ValidateHook': 'validate',  
}

FIELDS = ['file', 'size', 'mtime']

YUMCONF = ''' 
[main]
cachedir=
gpgcheck=0
reposdir=/
exclude=*debuginfo*

[%s]
name = %s - $basearch
baseurl = file://%s
'''

class IsoInterface(EventInterface, ListCompareMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    
    self.isodir = join(self.OUTPUT_DIR, 'iso')


#------ HOOKS ------#
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.init'
    
    self.interface = interface
  
  def run(self):
    parser = self.interface.getOptParser('build')

    # the following option doesn't work yet
    parser.add_option('--with-pkgorder',
                      default=None,
                      dest='with_pkgorder',
                      metavar='PKGORDERFILE',
                      help='use PKGORDERFILE for package ordering instead of generating it')

class ApplyoptHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.applyopt'
    
    self.interface = interface
                
  def run(self):
    if self.interface.options.with_pkgorder is not None:
      self.interface.cvars['pkgorder-file'] = self.interface.options.with_pkgorder


class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/iso', schemafile='iso.rng')


class ManifestHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.manifest'
    
    self.interface = interface
    
    self.mfile = join(self.interface.METADATA_DIR, 'manifest')
  
  def force(self):
    osutils.rm(self.mfile, force=True)
  
  def run(self):
    manifest = []
    for file in osutils.find(self.interface.SOFTWARE_STORE, prefix=False):
      manifest.append(
          self.__gen_manifest_line(file, prefix=self.interface.SOFTWARE_STORE)
        )
    
    if self._manifest_changed(manifest, self.mfile):
      if not exists(self.mfile): os.mknod(self.mfile)
      mf = open(self.mfile, 'w')
      mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
      for line in manifest:
        mwriter.writerow(line)
      mf.close()
  
  def apply(self):
    if not exists(self.mfile):
      raise RuntimeError, "Unable to find manifest file at '%s'" % self.mfile
  
  def __gen_manifest_line(self, file, prefix):
    fstat = os.stat(join(prefix, file))
    return {'file': file,
            'size': str(fstat.st_size),
            'mtime': str(fstat.st_mtime)}

  def _manifest_changed(self, manifest, old_manifest_file):
    if exists(old_manifest_file):
      mf = open(old_manifest_file, 'r')
      mreader = csv.DictReader(mf, FIELDS)
      old_manifest = []
      for line in mreader: old_manifest.append(line)
      mf.close()
      
      return manifest != old_manifest
    else:
      return True


class IsoHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.iso'
    
    self.interface = interface
    
    self.interface.lfn = self._delete_isotree
    self.interface.rfn = self._generate_isotree
    self.interface.bfn = self._check_isotree
    
    self.splittrees = join(self.interface.METADATA_DIR, 'iso/split-trees')
    
    self.DATA =  {
      'config':    ['/distro/iso'],
      'variables': ['interface.cvars[\'source-include\']'],
      'input':     [join(self.interface.METADATA_DIR, 'manifest')], 
      'output':    [self.interface.isodir,
                    self.splittrees], # may or may not want to include this one
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'iso.md')

    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def force(self):
    osutils.rm(self.interface.isodir, recursive=True, force=True)
    osutils.rm(self.splittrees, recursive=True, force=True)
    self.clean_metadata()
  
  def setup(self):
    pkgorderfile = self.interface.config.get('/distro/iso/pkgorder/text()', None)
    if pkgorderfile and not self.interface.cvars['pkgorder-file']:
      self.interface.cvars['pkgorder-file'] = pkgorderfile
  
  def check(self):
    if self.interface.config.get('/distro/iso/@enabled', 'True') in BOOLEANS_TRUE:
      if self.test_diffs():
        self.force()
        return True
    else:
      self.force() # clean up old output and metadata
    return False
  
  def run(self):
    self.interface.log(0, "generating iso image(s)")
    
    self.newsets = self.interface.config.xpath('/distro/iso/set/text()', [])
    self.newsets_expanded = []
    for set in self.newsets:
      self.newsets_expanded.append(splittree.parse_size(set))

    oldsets = filter(None, osutils.find(self.splittrees, type=osutils.TYPE_DIR,
                                        maxdepth=1, prefix=False))
    
    self.interface.compare(oldsets, self.newsets)

    self.write_metadata()
  
  def _generate_pkgorder(self):
    pkgorderfile = join(self.interface.METADATA_DIR, 'pkgorder')
    
    if self.interface.cvars['pkgorder-file']:
      self.interface.log(1, "using supplide package ordering file")
      pkgtups = pkgorder.parse_pkgorder(self.interface.cvars['pkgorder-file'])
    else:
      self.interface.log(1, "generating package ordering")
      cfg = join(self.interface.TEMP_DIR, 'pkgorder')
      
      repoid = self.interface.getBaseRepoId()
      
      filereader.write([YUMCONF % (repoid, repoid, self.interface.SOFTWARE_STORE)], cfg)
      
      pkgtups = pkgorder.order(config=cfg,
                               arch=self.interface.arch,
                               callback=BuildDepsolveCallback(self.interface.logthresh))
      
      osutils.rm(cfg, force=True)
  
    
    if exists(pkgorderfile):
      oldpkgorder = filereader.read(pkgorderfile)
    else:
      oldpkgorder = []
    
    old,new,_ = listcompare.compare(oldpkgorder, pkgtups)
    if len(new) > 0 or len(old) > 0:
      pkgorder.write_pkgorder(pkgorderfile, pkgtups)
    
  def _delete_isotree(self, set):
    expanded_set = splittree.parse_size(set)
    if expanded_set not in self.newsets_expanded:
      osutils.rm(join(self.splittrees, set), recursive=True, force=True)
    else:
      newset = self.newsets[self.newsets_expanded.index(expanded_set)]
      os.rename(join(self.splittrees, set),
                join(self.splittrees, newset))
      if newset in self.interface.r:
        self.interface.r.remove(newset) # don't create iso tree; it already exists
  
  def _generate_isotree(self, set):
    if not exists(join(self.interface.METADATA_DIR, 'pkgorder')):
      self._generate_pkgorder()
    
    osutils.mkdir(join(self.interface.isodir, set), parent=True)
    osutils.mkdir(join(self.splittrees, set), parent=True)
    
    splitter = splittree.Timber(set, dosrc=self.interface.cvars['source-include'])
    splitter.product = self.interface.product
    splitter.unified_tree = self.interface.SOFTWARE_STORE
    splitter.unified_source_tree = join(self.interface.DISTRO_DIR, 'SRPMS')
    splitter.split_tree = join(self.splittrees, set)
    splitter.difmt = locals_imerge(L_DISCINFO_FORMAT, self.interface.cvars['anaconda-version']).get('discinfo')
    splitter.pkgorder = join(self.interface.METADATA_DIR, 'pkgorder')
    
    self.interface.log(1, "splitting trees")
    self.interface.log(2, "computing layout")
    splitter.compute_layout()
    splitter.cleanup()
    self.interface.log(2, "splitting base files")
    splitter.split_trees()
    self.interface.log(2, "splitting rpms")
    splitter.split_rpms()
    self.interface.log(2, "splitting srpms")
    splitter.split_srpms()
    
    for i in range(1, splitter.numdiscs + 1):
      iso = '%s-disc%d' % (self.interface.product, i)
      self.interface.log(1, "generating %s.iso" % iso)
      isolinux_stat = os.stat(join(self.splittrees, set, iso, 'isolinux/isolinux.bin'))
      if i == 1: # the first disc needs to be made bootable
        bootargs = '-b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table'
      else:
        bootargs = ''
      shlib.execute('mkisofs %s -UJRTV "%s" -o %s.iso %s' % \
         (bootargs,
          '%s %s %s disc %d' % \
                       (self.interface.product,
                        self.interface.version,
                        self.interface.release,
                        i),
          join(self.interface.isodir, set, iso),
          join(self.splittrees, set, iso)),
        verbose=True)
      
      if i == 1: # reset mtimte on isolinux.bin (mkisofs is so misbehaved in this regard)
        os.utime(join(self.splittrees, set, iso, 'isolinux/isolinux.bin'),
                 (isolinux_stat.st_atime, isolinux_stat.st_mtime))
  
  def _check_isotree(self, set):
    for disc in (osutils.find(join(self.splittrees, set),
                              name='%s-disc*' % self.interface.product,
                              type=osutils.TYPE_DIR,
                              maxdepth=1,
                              prefix=False)):
      if not exists(join(self.interface.isodir, set, '%s.iso' % disc)):
        self._delete_isotree(set)
        self._generate_isotree(set)

L_DISCINFO_FORMAT = ''' 
<locals>
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
        <string-format string="%s">
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
        <string-format string="%s">
          <format>
            <item>product</item>
          </format>
        </string-format>
      </line>
    </discinfo>
  </discinfo-entries>
</locals>
'''
