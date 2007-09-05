from dims import filereader
from dims import pkgorder
from dims import shlib

from dimsbuild import splittree

from dimsbuild.callback    import BuildDepsolveCallback
from dimsbuild.constants   import BOOLEANS_TRUE
from dimsbuild.difftest    import NewEntry
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
    'conditional-requires': ['manifest-changed', 'sources-enabled', 'srpms'],
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
    
    self.isodir = self.OUTPUT_DIR/'iso'
    
    self.ISO_METADATA_DIR = self.METADATA_DIR/'iso'
    
    self.cvars['iso-enabled'] = self.config.pathexists('/distro/iso') and \
                                self.config.get('/distro/iso/@enabled', 'True') in BOOLEANS_TRUE


#------ HOOKS ------#
class IsoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'iso.ISO'
    self.interface = interface
  
  def setup(self):
    if not self.interface.ISO_METADATA_DIR.exists():
      self.interface.ISO_METADATA_DIR.mkdirs()

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
      'variables': ['cvars[\'iso-enabled\']',
                    'cvars[\'pkglist\']'],
      'config':    ['/distro/iso/pkgorder'],
      'output':    []
    }
    self.mdfile = self.interface.ISO_METADATA_DIR/'pkgorder.md'
    self.dosync = self.interface.config.pathexists('/distro/iso/pkgorder/text()')
    if self.dosync:
      self.DATA['input'] = []
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    if not self.interface.cvars['iso-enabled']: return
    
    if self.dosync:
      self.interface.setup_sync(self.interface.ISO_METADATA_DIR, id='pkgorder',
                                xpaths=['/distro/iso/pkgorder'])
      self.pkgorderfile = self.interface.list_output(what='pkgorder')[0]
    else:
      self.pkgorderfile = self.interface.ISO_METADATA_DIR/'pkgorder'
      self.DATA['output'].append(self.pkgorderfile)
      
  def clean(self):
    self.interface.log(0, "cleaning pkgorder event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    # changing from iso-enabled true, cleanup old files and metadata
    if self.interface.var_changed_from_true('cvars[\'iso-enabled\']'):
      self.clean()
    
    if not self.interface.cvars['iso-enabled']: 
      self.interface.write_metadata()
      return
    
    self.interface.log(0, "processing pkgorder file")
    
    # delete prior pkgorder file, if exists    
    self.interface.remove_output(all=True)
    if self.dosync:
      self.interface.sync_input()
    else:
      # generate pkgorder
      self.interface.log(1, "generating package ordering")
      
      # create yum config needed by pkgorder
      cfg = self.interface.TEMP_DIR/'pkgorder'
      repoid = self.interface.getBaseRepoId()
      filereader.write([YUMCONF % (repoid, repoid, self.interface.SOFTWARE_STORE)], cfg)
      
      # create pkgorder
      pkgtups = pkgorder.order(config=cfg,
                               arch=self.interface.arch,
                               callback=BuildDepsolveCallback(self.interface.logthresh))
      
      # cleanup
      cfg.remove()
      
      # write pkgorder
      pkgorder.write_pkgorder(self.pkgorderfile, pkgtups)      
    
    self.interface.write_metadata()
  
  def apply(self):
    if self.interface.cvars['iso-enabled']:
      if not self.pkgorderfile.exists():
        raise RuntimeError("Unable to find cached pkgorder at '%s'. "\
                           "Perhaps you are skipping the pkgorder event "\
                           "before it has been allowed to run once?" % self.pkgorderfile)
      self.interface.cvars['pkgorder-file'] = self.pkgorderfile

class IsoSetsHook:
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'iso.iso-sets'
    
    self.interface = interface
    
    self.interface.lfn = self._delete_isotree
    self.interface.rfn = self._generate_isotree
    
    self.splittrees = self.interface.ISO_METADATA_DIR/'split-trees'
    
    self.DATA =  {
      'variables': ['cvars[\'iso-enabled\']'],
      'config':    [],
      'input':     [], 
      'output':    [],
    }

    self.mdfile = self.interface.ISO_METADATA_DIR/'iso.md'
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    
    if not self.interface.cvars['iso-enabled']: return
    
    self.DATA['config'].extend(['/distro/iso/set/text()',
                                'cvars[\'sources-enabled\']',
                                'cvars[\'srpms\']',])
    self.DATA['input'].append(self.interface.cvars['pkgorder-file'])
  
  def clean(self):
    self.interface.log(0, "cleaning iso event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    # changing from iso-enabled true, cleanup old files and metadata
    if self.interface.var_changed_from_true('cvars[\'iso-enabled\']'):
      self.clean()
    
    if not self.interface.cvars['iso-enabled']: 
      self.interface.write_metadata()
      return
    
    self.interface.log(0, "processing iso image(s)")
    
    oldsets = None

    # remove oldsets if pkgorder file, srpms, or sources-enabled changed
    if self.interface.handlers['input'].diffdict or \
       self.interface.handlers['variables'].diffdict.has_key("cvars['srpms']") or \
       self.interface.handlers['variables'].diffdict.has_key("cvars['sources-enabled']"):
      self.interface.remove_output(all=True)
      oldsets = []

    # otherwise get oldsets from metadata file
    if oldsets is None:    
      try: 
        oldsets = self.interface.handlers['config'].cfg['/distro/iso/set/text()']
      except KeyError:
        oldsets = []

    newsets = self.interface.config.xpath('/distro/iso/set/text()', [])
     
    self.newsets_expanded = []
    for set in newsets:
      self.newsets_expanded.append(splittree.parse_size(set))
      
    self.interface.compare(oldsets, newsets)
    
    self.DATA['output'].extend([self.interface.isodir, self.splittrees])
    
    self.interface.write_metadata()
  
  def _delete_isotree(self, set):
    expanded_set = splittree.parse_size(set)
    if expanded_set not in self.newsets_expanded:
      self.interface.remove_output(rmlist=[self.splittrees/set,
                                           self.interface.isodir/set])
    else:
      newset = self.newsets[self.newsets_expanded.index(expanded_set)]
      (self.splittrees/set).rename(self.splittrees/newset)
      if newset in self.interface.r:
        self.interface.r.remove(newset) # don't create iso tree; it already exists
  
  def _generate_isotree(self, set):
    self.interface.log(1, "generating iso tree '%s'" % set)
    (self.interface.isodir/set).mkdirs()
    (self.splittrees/set).mkdirs()
    
    splitter = splittree.Timber(set, dosrc=self.interface.cvars['sources-enabled'])
    splitter.product = self.interface.product
    splitter.u_tree     = self.interface.SOFTWARE_STORE
    splitter.u_src_tree = self.interface.OUTPUT_DIR/'SRPMS'
    splitter.s_tree     = self.splittrees/set
    splitter.difmt = locals_imerge(L_DISCINFO_FORMAT, self.interface.cvars['anaconda-version']).get('discinfo')
    splitter.pkgorder = self.interface.cvars['pkgorder-file']
    
    self.interface.log(2, "splitting trees")
    self.interface.log(3, "computing layout")
    splitter.compute_layout()
    splitter.cleanup()
    self.interface.log(3, "splitting base files")
    splitter.split_trees()
    self.interface.log(3, "splitting rpms")
    splitter.split_rpms()
    self.interface.log(3, "splitting srpms")
    splitter.split_srpms()
    
    for i in range(1, splitter.numdiscs + 1):
      iso = '%s-disc%d' % (self.interface.product, i)
      self.interface.log(2, "generating %s.iso" % iso)
      if i == 1: # the first disc needs to be made bootable
        isolinux_path = self.splittrees/set/iso/'isolinux/isolinux.bin'
        i_st = isolinux_path.stat()
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
          self.interface.isodir/set/iso,
          self.splittrees/set/iso),
        verbose=True)
      
      if i == 1: # reset mtimte on isolinux.bin (mkisofs is so misbehaved in this regard)
        isolinux_path.utime((i_st.st_atime, i_st.st_mtime))
  

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
