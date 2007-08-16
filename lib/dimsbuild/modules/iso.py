import csv
import os

from os.path import join, exists

from dims import filereader
from dims import pkgorder
from dims import listcompare
from dims import osutils
from dims import shlib

from dimsbuild import splittree

from dimsbuild.callback    import BuildDepsolveCallback
from dimsbuild.constants   import BOOLEANS_TRUE
from dimsbuild.event       import EVENT_TYPE_MDLR, EVENT_TYPE_PROC, EVENT_TYPE_META
from dimsbuild.interface   import EventInterface 
from dimsbuild.modules.lib import ListCompareMixin
from dimsbuild.misc        import locals_imerge

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'ISO',
    'interface': 'IsoInterface',
    'properties': EVENT_TYPE_META,
    'conditional-requires': ['MAIN', 'manifest'],
    'provides': ['iso-enabled'],
    'parent': 'ALL',
  },
  {
    'id': 'pkgorder',
    'interface': 'IsoInterface',
    'properties': EVENT_TYPE_MDLR|EVENT_TYPE_PROC,
    'requires': ['pkglist'],
    'provides': ['pkgorder-file'],
    'parent': 'ISO',
  },
  {
    'id': 'iso-sets',
    'interface': 'IsoInterface',
    'properties': EVENT_TYPE_MDLR|EVENT_TYPE_PROC,
    'requires': ['anaconda-version', 'pkgorder-file'],
    'conditional-requires': ['manifest-changed', 'source-include'],
    'parent': 'ISO',
  },
]

HOOK_MAPPING = {
  'IsoHook':      'ISO',
  'PkgorderHook': 'pkgorder',
  'IsoSetsHook':  'iso-sets',
  'ValidateHook': 'validate',  
}

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

    self.ISO_METADATA_DIR = join(self.METADATA_DIR, 'iso')

    self.cvars['iso-enabled'] = self.config.get('/distro/source', '') != '' and \
      self.config.get('/distro/iso/@enabled', 'True') in BOOLEANS_TRUE

#------ HOOKS ------#
class IsoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso'
    self.interface = interface

  def setup(self):
    if not exists(self.interface.ISO_METADATA_DIR): 
      osutils.mkdir(self.interface.ISO_METADATA_DIR)

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/iso', schemafile='iso.rng')

class PkgorderHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.iso'
    
    self.interface = interface

    self.DATA =  {
      'variables': ['interface.cvars[\'iso-enabled\']',
                    'interface.cvars[\'pkglist\']'],
      'config':    ['/distro/iso/pkgorder'],
      'input':     [], 
      'output':    []
    }
    self.mdfile = join(self.interface.ISO_METADATA_DIR, 'pkgorder.md')

  def setup(self):    
    if self.interface.cvars['iso-enabled']:
      #set variables used in run and apply functions
      self.pkgorder_in = self.interface.config.get('/distro/iso/pkgorder/text()', None)

      if self.pkgorder_in: 
        self.pkgorder_out = join(self.interface.ISO_METADATA_DIR, self.pkgorder_in)
      else: 
        self.pkgorder_out = join(self.interface.ISO_METADATA_DIR, 'pkgorder')

    self.interface.setup_diff(self.mdfile, self.DATA)
    
    # add files to the input and output filelists - see FilesMixin.add_files() in lib.py
    # TODO - once FilesMixin accepts paths, pass pkgorder_in var to add_files
    i,o = self.interface.getFileLists(xpaths=[('/distro/iso/pkgorder',
                                               osutils.dirname(self.interface.config.file),
                                               self.interface.ISO_METADATA_DIR)])
    self.DATA['input'].extend(i)
    self.DATA['output'].extend(o)    
      
  def clean(self):
    self._remove_output()
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()

  def run(self):
    if self.interface.cvars['iso-enabled']:
      self.interface.log(0, "processing pkgorder file")

      # delete prior pkgorder file, if exists
      if self.interface.handlers['output'].oldoutput.keys():
        self.interface.log(1, "removing prior pkgorder file")
        self.interface.remove_output(all=True)

      if self.pkgorder_in:    
        # download pkgorder file, if provided
        self.interface.log(1, "adding new pkgorder file")
        self.interface.sync_input()

      else:
        # generate pkgorder
        self.interface.log(1, "generating package ordering")

        # create yum config needed by pkgorder
        cfg = join(self.interface.TEMP_DIR, 'pkgorder')
        repoid = self.interface.getBaseRepoId()
        filereader.write([YUMCONF % (repoid, repoid, self.interface.SOFTWARE_STORE)], cfg)

        # create pkgorder
        pkgtups = pkgorder.order(config=cfg,
                                 arch=self.interface.arch,
                                 callback=BuildDepsolveCallback(self.interface.logthresh))
        pkgorder.write_pkgorder(self.pkgorder_out, pkgtups)

        # update output data
        self.DATA['output'].append(self.pkgorder_out)

        # cleanup
        osutils.rm(cfg, force=True)

    else:
      # iso not enabled, clean up old pkgorder
      self._remove_output()

    # write metadata
    self.interface.write_metadata()

  def apply(self):
    #set pkgorder-file variable
    if self.interface.cvars['iso-enabled']:
      if exists(self.pkgorder_out):
        self.interface.cvars['pkgorder-file'] = self.pkgorder_out
      else:
        raise RuntimeError("Unable to find cached pkgorder at '%s'. Perhaps you are skipping the pkgorder event before it has been allowed to run once?" % self.pkgorder_out)

  def _remove_output(self):
    # print a header message only if a pkgorder file exists to remove
    files_exist = False
    for item in self.interface.handlers['output'].oldoutput.keys():
      if exists(item):
        files_exist = True
        continue
    if files_exist:
      self.interface.log(0, "removing pkgorder file")
      self.interface.remove_output(all=True)

class IsoSetsHook:
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'iso.iso-sets'
    
    self.interface = interface
    
    self.interface.lfn = self._delete_isotree
    self.interface.rfn = self._generate_isotree
    
    self.splittrees = join(self.interface.ISO_METADATA_DIR, 'split-trees')
    
    self.DATA =  {
      'config':    ['//iso/set'],
      'variables': ['interface.cvars[\'source-include\']',
                    'interface.cvars[\'iso-enabled\']'],
      'input':     [], 
      'output':    []
    }

    self.mdfile = join(self.interface.ISO_METADATA_DIR, 'iso.md')
  
  def setup(self):
    if self.interface.cvars['iso-enabled']:
      self.DATA['input'].append(self.interface.cvars['pkgorder-file'])
    self.interface.setup_diff(self.mdfile, self.DATA)

  def clean(self):
    self._remove_output()
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    if self.interface.cvars['iso-enabled']:

      self.interface.log(0, "generating iso image(s)")
    
      # get list of new sets
      self.newsets = self.interface.config.xpath('/distro/iso/set/text()', [])
      self.newsets_expanded = []
      for set in self.newsets:
        self.newsets_expanded.append(splittree.parse_size(set))

      if self.interface.handlers['input'].idiff or \
         self.interface.handlers['variables'].vdiff.has_key("interface.cvars['source-include']"):
        osutils.rm(self.interface.isodir, recursive=True, force=True)
        osutils.rm(self.splittrees, recursive=True, force=True)        
        #osutils.rm(self.handlers['output'].oldoutput.keys(), recursive=True, force=True)

      # get current list of prior sets
      oldsets = filter(None, osutils.find(self.splittrees, type=osutils.TYPE_DIR,
                       maxdepth=1, printf='%P'))

      self.interface.compare(oldsets, self.newsets)

      self.DATA['output'].extend([self.interface.isodir,
                                  self.splittrees])
    else:
      # iso not enabled, clean up old output and metadata
      # TODO - only do this if prior output exists
      self._remove_output() 

  def apply(self):
    self.interface.write_metadata()

  def _remove_output(self):
    # TODO generalize remove_files from the FilesMixin and use it here
    if exists(self.interface.isodir) or exists(self.splittrees):
      self.interface.log(0, "removing iso image(s)")
      osutils.rm(self.interface.isodir, recursive=True, force=True)
      osutils.rm(self.splittrees, recursive=True, force=True)
  
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
    osutils.mkdir(join(self.interface.isodir, set), parent=True)
    osutils.mkdir(join(self.splittrees, set), parent=True)
    
    splitter = splittree.Timber(set, dosrc=self.interface.cvars['source-include'])
    splitter.product = self.interface.product
    splitter.unified_tree = self.interface.SOFTWARE_STORE
    splitter.unified_source_tree = join(self.interface.OUTPUT_DIR, 'SRPMS')
    splitter.split_tree = join(self.splittrees, set)
    splitter.difmt = locals_imerge(L_DISCINFO_FORMAT, self.interface.cvars['anaconda-version']).get('discinfo')
    splitter.pkgorder = self.interface.cvars['pkgorder-file']
    
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
      if i == 1: # the first disc needs to be made bootable
        isolinux_stat = os.stat(join(self.splittrees, set, iso, 'isolinux/isolinux.bin'))
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
