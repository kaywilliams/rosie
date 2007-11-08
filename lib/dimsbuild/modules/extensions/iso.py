from dims import pkgorder
from dims import shlib

from dimsbuild import splittree

from dimsbuild.callback    import BuildDepsolveCallback
from dimsbuild.constants   import BOOLEANS_TRUE
from dimsbuild.event       import Event, CLASS_META
from dimsbuild.logging     import L1, L2, L3

from dimsbuild.modules.shared import ListCompareMixin, BootConfigMixin

API_VERSION = 5.0
EVENTS = {'ALL': ['IsoMetaEvent'], 'ISO': ['PkgorderEvent', 'IsoSetsEvent']}

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
      properties = CLASS_META,
    )
    

class PkgorderEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pkgorder',
      provides = ['pkgorder-file'],
      requires = ['repodata-directory', 'os-dir'],
    )
    
    self.DATA =  {
      'config':    ['pkgorder'],
      'input':     [],
      'output':    []
    }
    
    self.dosync = self.config.pathexists('pkgorder/text()')
    if self.dosync: self.DATA['input'] = [] # huh?
  
  def setup(self):
    self.diff.setup(self.DATA)
    
    self.DATA['input'].append(self.cvars['repodata-directory'])
    
    if self.dosync:
      self.io.setup_sync(self.mddir, id='pkgorder',
                         xpaths=['pkgorder'])
      self.pkgorderfile = self.io.list_output(what='pkgorder')[0]
    else:
      self.pkgorderfile = self.mddir/'pkgorder'
      self.DATA['output'].append(self.pkgorderfile)
  
  def run(self):
    # delete prior pkgorder file, if exists    
    self.io.clean_eventcache(all=True)
    if self.dosync:
      self.io.sync_input(cache=True)
    else:
      # generate pkgorder
      self.log(1, L1("generating package ordering"))
      
      # create yum config needed by pkgorder
      cfg = self.TEMP_DIR/'pkgorder'
      repoid = self.pva
      cfg.write_lines([ YUMCONF % (self.pva, self.pva, self.cvars['os-dir']) ])
      
      # create pkgorder
      pkgtups = pkgorder.order(config=cfg,
                               arch=self.arch,
                               callback=BuildDepsolveCallback(self.logger))
      
      # cleanup
      cfg.remove()
      
      # write pkgorder
      pkgorder.write_pkgorder(self.pkgorderfile, pkgtups)
    
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    self.cvars['pkgorder-file'] = self.pkgorderfile
  
  def verify_pkgorder_exists(self):
    "verify pkgorder file exists"
    self.verifier.failUnless(self.pkgorderfile.exists(),
      "unable to find pkgorder file at '%s'" % self.pkgorderfile)


class IsoSetsEvent(Event, ListCompareMixin, BootConfigMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'iso',
      provides = ['iso-dir', 'publish-content'],
      requires = ['anaconda-version', 'pkgorder-file', 'manifest-file',
                  'boot-config-file', 'os-dir'],
      conditionally_requires = ['srpms-dir', 'ks-path', 'boot-args'],
    )
    ListCompareMixin.__init__(self)
    BootConfigMixin.__init__(self)
    
    self.lfn = self._delete_isotree
    self.rfn = self._generate_isotree
    self.bfn = self._extend_diffdata
    
    self.splittrees = self.mddir/'split-trees'
    
    self.DATA =  {
      'config':    ['.'],
      'variables': ['cvars[\'srpms\']', 'cvars[\'ks-path\']'],
      'input':     [],
      'output':    [],
    }
    
  def setup(self):
    self.diff.setup(self.DATA)
    self.isodir = self.mddir/'iso'
    
    self.DATA['input'].append(self.cvars['pkgorder-file'])
    self.DATA['input'].append(self.cvars['manifest-file'])
    
    default_boot_args = ['method=cdrom']
    self.bootconfig._process_ks(default_boot_args)
    self.bootconfig.setup(defaults=default_boot_args)
  
  def run(self):
    oldsets = None
    
    # remove oldsets if pkgorder file or srpms changed
    if self.diff.handlers['input'].diffdict or \
       self.diff.handlers['variables'].diffdict.has_key("cvars['srpms']"):
      self.io.clean_eventcache(all=True)
      oldsets = []
    
    # otherwise get oldsets from metadata file
    if oldsets is None:
      try:
        oldsets = self.diff.handlers['config'].cfg['set/text()']
      except KeyError:
        oldsets = []
    
    newsets = self.config.xpath('set/text()', [])
    
    self.newsets_expanded = []
    for set in newsets:
      self.newsets_expanded.append(splittree.parse_size(set))
    
    self.compare(oldsets, newsets)
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    self.cvars['iso-dir'] = self.isodir
    try: self.cvars['publish-content'].add(self.isodir)
    except: pass
  
  def _extend_diffdata(self, set):
    self.DATA['output'].extend([self.splittrees/set, self.isodir/set])

  def _delete_isotree(self, set):
    expanded_set = splittree.parse_size(set)
    if expanded_set in self.newsets_expanded:
      newset = self.newsets[self.newsets_expanded.index(expanded_set)]
      (self.splittrees/set).rename(self.splittrees/newset)
      self.DATA['output'].extend([self.splittrees/set, self.isodir/set])
      if newset in self.r:
        self.r.remove(newset) # don't create iso tree; it already exists
  
  def _generate_isotree(self, set):
    self.log(1, L1("generating iso tree '%s'" % set))
    (self.isodir/set).mkdirs()
    (self.splittrees/set).mkdirs()
    
    splitter = splittree.Timber(set, dosrc=self.cvars['srpms-dir'] is not None)
    splitter.product = self.product
    splitter.u_tree     = self.cvars['os-dir']
    splitter.u_src_tree = self.cvars['srpms-dir']
    splitter.s_tree     = self.splittrees/set
    splitter.difmt = self.locals.discinfo_fmt
    splitter.pkgorder = self.cvars['pkgorder-file']
    
    self.log(2, L2("splitting trees"))
    self.log(3, L3("computing layout"))
    splitter.compute_layout()
    splitter.cleanup()
    self.log(3, L3("splitting base files"))
    splitter.split_trees()
    # modify boot args on isolinux.cfg file(s)
    for cfg in splitter.s_tree.findpaths(glob='isolinux.cfg'):
      self.bootconfig.modify(cfg)
    self.log(3, L3("splitting rpms"))
    splitter.split_rpms()
    self.log(3, L3("splitting srpms"))
    splitter.split_srpms()
    
    for i in range(1, splitter.numdiscs + 1):
      iso = '%s-disc%d' % (self.product, i)
      self.log(2, L2("generating '%s/%s.iso'" % (set, iso)))
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

    self.DATA['output'].extend([self.splittrees/set, self.isodir/set])
