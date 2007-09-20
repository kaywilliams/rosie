from dims import filereader
from dims import pkgorder
from dims import shlib

from dims.dispatch import PROPERTY_META

from dimsbuild import splittree

from dimsbuild.callback    import BuildDepsolveCallback
from dimsbuild.constants   import BOOLEANS_TRUE
from dimsbuild.event       import Event
from dimsbuild.logging     import L0, L1, L2, L3
from dimsbuild.modules.lib import ListCompareMixin
from dimsbuild.misc        import locals_imerge

API_VERSION = 5.0

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

class IsoMetaEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'ISO',
      properties = PROPERTY_META,
      provides = ['iso-enabled'],
      comes_after = ['MAIN'],
    )
    
    self.cvars['iso-enabled'] = self.config.pathexists('/distro/iso') and \
                                self.config.get('/distro/iso/@enabled', 'True') in BOOLEANS_TRUE


class PkgorderEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pkgorder',
      provides = ['pkgorder-file'],
      requires = ['repodata-directory', 'composed-tree'],
    )
    
    self.DATA =  {
      'variables': ['cvars[\'iso-enabled\']'],
      'config':    ['/distro/iso/pkgorder'],
      'input':     [],
      'output':    []
    }
    
    self.dosync = self.config.pathexists('/distro/iso/pkgorder/text()')
    if self.dosync: self.DATA['input'] = [] # huh?
  
  def setup(self):
    self.setup_diff(self.DATA)
    if not self.cvars['iso-enabled']: return

    self.DATA['input'].append(self.cvars['repodata-directory'])
    
    if self.dosync:
      self.setup_sync(self.mddir, id='pkgorder',
                      xpaths=['/distro/iso/pkgorder'])
      self.pkgorderfile = self.list_output(what='pkgorder')[0]
    else:
      self.pkgorderfile = self.mddir/'pkgorder'
      self.DATA['output'].append(self.pkgorderfile)
  
  def run(self):
    # changing from iso-enabled true, cleanup old files and metadata
    if self.var_changed_from_value('cvars[\'iso-enabled\']', True):
      self.clean()
    
    if not self.cvars['iso-enabled']: 
      self.write_metadata()
      return
    
    self.log(0, L0("processing pkgorder file"))
    
    # delete prior pkgorder file, if exists    
    self.remove_output(all=True)
    if self.dosync:
      self.sync_input()
    else:
      # generate pkgorder
      self.log(1, L1("generating package ordering"))
      
      # create yum config needed by pkgorder
      cfg = self.TEMP_DIR/'pkgorder'
      repoid = self.pva
      filereader.write([YUMCONF % (self.pva, self.pva, self.DISTRO_DIR/'output/os')], cfg)
      
      # create pkgorder
      pkgtups = pkgorder.order(config=cfg,
                               arch=self.arch,
                               callback=BuildDepsolveCallback(self.logger))
      
      # cleanup
      cfg.remove()
      
      # write pkgorder
      pkgorder.write_pkgorder(self.pkgorderfile, pkgtups)      
    
    self.write_metadata()
  
  def apply(self):
    if self.cvars['iso-enabled']:
      if not self.pkgorderfile.exists():
        raise RuntimeError("Unable to find cached pkgorder at '%s'.  "
                           "Perhaps you are skipping the pkgorder event "
                           "before it has been allowed to run once?" % self.pkgorderfile)
      self.cvars['pkgorder-file'] = self.pkgorderfile


class IsoSetsEvent(Event, ListCompareMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'iso',
      requires = ['anaconda-version', 'pkgorder-file', 'composed-tree'],
      conditionally_requires = ['manifest-changed', 'sources-enabled', 'srpms'],
    )
    ListCompareMixin.__init__(self)
    
    self.lfn = self._delete_isotree
    self.rfn = self._generate_isotree
    
    self.splittrees = self.mddir/'split-trees'
    
    self.DATA =  {
      'variables': ['cvars[\'iso-enabled\']'],
      'config':    [],
      'input':     [], 
      'output':    [],
    }
    
    self.output_dir = self.DISTRO_DIR/'output'

  def validate(self):
    self.validator.validate('/distro/iso', 'iso.rng')
  
  def setup(self):
    self.setup_diff(self.DATA)
    
    self.isodir = self.mddir/'iso'
    
    if not self.cvars['iso-enabled']: return
    
    self.DATA['config'].extend(['/distro/iso/set/text()',
                                'cvars[\'sources-enabled\']',
                                'cvars[\'srpms\']',])
    self.DATA['input'].append(self.cvars['pkgorder-file'])
  
  def run(self):
    # changing from iso-enabled true, cleanup old files and metadata
    if self.var_changed_from_value('cvars[\'iso-enabled\']', True):
      self.clean()
    
    if not self.cvars['iso-enabled']: 
      self.write_metadata()
      return
    
    self.log(0, L0("processing iso image(s)"))
    
    oldsets = None
    
    # remove oldsets if pkgorder file, srpms, or sources-enabled changed
    if self._diff_handlers['input'].diffdict or \
       self._diff_handlers['variables'].diffdict.has_key("cvars['srpms']") or \
       self._diff_handlers['variables'].diffdict.has_key("cvars['sources-enabled']"):
      self.remove_output(all=True)
      oldsets = []
    
    # otherwise get oldsets from metadata file
    if oldsets is None:    
      try: 
        oldsets = self._diff_handlers['config'].cfg['/distro/iso/set/text()']
      except KeyError:
        oldsets = []
    
    newsets = self.config.xpath('/distro/iso/set/text()', [])
    
    self.newsets_expanded = []
    for set in newsets:
      self.newsets_expanded.append(splittree.parse_size(set))
    
    self.compare(oldsets, newsets)
    
    self.DATA['output'].extend([self.isodir, self.splittrees])
    
    self.write_metadata()
  
  def apply(self):
    # copy iso sets into composed tree
    self.isodir.cp(self.output_dir, recursive=True, link=True)
  
  def _delete_isotree(self, set):
    expanded_set = splittree.parse_size(set)
    if expanded_set not in self.newsets_expanded:
      self.remove_output(rmlist=[self.splittrees/set,
                                 self.isodir/set])
    else:
      newset = self.newsets[self.newsets_expanded.index(expanded_set)]
      (self.splittrees/set).rename(self.splittrees/newset)
      if newset in self.r:
        self.r.remove(newset) # don't create iso tree; it already exists
  
  def _generate_isotree(self, set):
    self.log(1, L1("generating iso tree '%s'" % set))
    (self.isodir/set).mkdirs()
    (self.splittrees/set).mkdirs()
    
    splitter = splittree.Timber(set, dosrc=self.cvars['sources-enabled'])
    splitter.product = self.product
    splitter.u_tree     = self.output_dir/'os'
    splitter.u_src_tree = self.output_dir/'SRPMS'
    splitter.s_tree     = self.splittrees/set
    splitter.difmt = locals_imerge(L_DISCINFO_FORMAT, self.cvars['anaconda-version']).get('discinfo')
    splitter.pkgorder = self.cvars['pkgorder-file']
    
    self.log(2, L2("splitting trees"))
    self.log(3, L3("computing layout"))
    splitter.compute_layout()
    splitter.cleanup()
    self.log(3, L3("splitting base files"))
    splitter.split_trees()
    self.log(3, L3("splitting rpms"))
    splitter.split_rpms()
    self.log(3, L3("splitting srpms"))
    splitter.split_srpms()
    
    for i in range(1, splitter.numdiscs + 1):
      iso = '%s-disc%d' % (self.product, i)
      self.log(2, L2("generating %s.iso" % iso))
      if i == 1: # the first disc needs to be made bootable
        isolinux_path = self.splittrees/set/iso/'isolinux/isolinux.bin'
        i_st = isolinux_path.stat()
        bootargs = '-b isolinux/isolinux.bin -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table'
      else:
        bootargs = ''
      shlib.execute('mkisofs %s -UJRTV "%s" -o %s.iso %s' % \
         (bootargs,
          '%s %s %s disc %d' % \
            (self.product, self.version, self.release, i),
          self.isodir/set/iso,
          self.splittrees/set/iso),
        verbose=True)
      
      if i == 1: # reset mtimte on isolinux.bin (mkisofs is so misbehaved in this regard)
        isolinux_path.utime((i_st.st_atime, i_st.st_mtime))
  

EVENTS = {'ALL': [IsoMetaEvent], 'ISO': [PkgorderEvent, IsoSetsEvent]}


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
