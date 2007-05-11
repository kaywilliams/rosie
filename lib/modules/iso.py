import csv
import os

from os.path import join, exists

import dims.filereader  as filereader
import dims.pkgorder    as pkgorder
import dims.listcompare as listcompare
import dims.osutils     as osutils
import dims.shlib       as shlib

import splittree

from callback  import BuildDepsolveCallback
from event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface import EventInterface, ListCompareMixin, LocalsMixin
from locals    import L_DISCINFO

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'manifest',
    'requires': ['MAIN'],
    'provides': ['manifest'],
    'parent': 'ALL',
  },
  {
    'id': 'pkgorder',
    'requires': ['pkglist', 'RPMS', 'software'],
    'provides': ['pkgorder'],
    'properties': EVENT_TYPE_MDLR|EVENT_TYPE_PROC,
  },
  {
    'id': 'iso',
    'requires': ['manifest', 'pkgorder'],
    'provides': ['iso'],
    'parent': 'ALL',
    'interface': 'IsoInterface',
    'properties': EVENT_TYPE_MDLR|EVENT_TYPE_PROC,
  },
]

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

class IsoInterface(EventInterface, ListCompareMixin, LocalsMixin):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    ListCompareMixin.__init__(self)
    LocalsMixin.__init__(self, join(self.getMetadata(), '%s.pkgs' % self.getBaseStore()),
                         self._base.IMPORT_DIRS)
    self.isodir = join(osutils.dirname(self.getSoftwareStore()), 'iso')

def prepkgorder_hook(interface):
  interface.disableEvent('pkgorder')
  if interface.get_cvar('pkglist-changed'):
    interface.enableEvent('pkgorder')
  elif not exists(join(interface.getMetadata(), 'pkgorder')):
    interface.enableEvent('pkgorder')

def pkgorder_hook(interface):
  interface.log(0, "generating package ordering")
  cfg = join(interface.getTemp(), 'pkgorder')
  
  filereader.write([YUMCONF % (interface.getBaseStore(),
                               interface.getBaseStore(),
                               interface.getSoftwareStore())], cfg)
  
  pkgtups = pkgorder.order(config=cfg,
                           arch=interface.arch,
                           callback=BuildDepsolveCallback(interface.logthresh))
  
  pkgorder.write_pkgorder(join(interface.getMetadata(), 'pkgorder'), pkgtups)
  
  osutils.rm(cfg, force=True)

def manifest_hook(interface):
  interface.set_cvar('do-iso', False)
  manifest = []
  for file in osutils.tree(interface.getSoftwareStore(), prefix=False):
    manifest.append(__gen_manifest_line(join(interface.getSoftwareStore(), file)))
  
  mfile = join(interface.getMetadata(), 'manifest')
  if manifest_changed(manifest, mfile):
    interface.set_cvar('do-iso', True)      
    if not exists(mfile): os.mknod(mfile)
    mf = open(mfile, 'w')
    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)
    mf.close()

def __gen_manifest_line(file):
  fstat = os.stat(file)
  return {'file': file,
          'size': str(fstat.st_size),
          'mtime': str(fstat.st_mtime)}

def manifest_changed(manifest, old_manifest_file):
  if exists(old_manifest_file):
    mf = open(old_manifest_file, 'r')
    mreader = csv.DictReader(mf, FIELDS)
    old_manifest = []
    for line in mreader: old_manifest.append(line)
    mf.close()
    
    return manifest != old_manifest
  else:
    return True

def preiso_hook(interface):
  interface.disableEvent('iso')
  if interface.eventForceStatus('iso') or False:
    interface.enableEvent('iso')
  elif interface.get_cvar('do-iso'):
    interface.enableEvent('iso')

def iso_hook(interface):
  interface.log(0, 'generating iso image(s)')

  handler = IsoHandler(interface)
  handler.handle()


class IsoHandler:
  def __init__(self, interface):
    self.interface = interface
    self.interface.lfn = self.delete_isotree
    self.interface.rfn = self.generate_isotree
    self.interface.bfn = self.check_isotree
    
    self.newsets = self.interface.config.mget('//iso/set/@size', [])
    self.newsets_expanded = []
    for set in self.newsets:
      self.newsets_expanded.append(splittree.parse_size(set))
  
  def handle(self):
    "Generate isos"
    
    oldsets = filter(None, osutils.find(self.interface.isodir, type=osutils.TYPE_DIR,
                           maxdepth=1, prefix=False))
    self.interface.compare(oldsets, self.newsets)
    
    for iso in osutils.find(self.interface.isodir, type=osutils.TYPE_DIR,
                            mindepth=2, maxdepth=2, prefix=False):
      
      self.interface.log(1, "generating %s.iso" % osutils.basename(iso))
      ## add -quiet and remove verbose when done testing
      shlib.execute('mkisofs -UJRTV "%s" -o %s.iso %s' % \
        ('%s %s %s' % (self.interface.product,
                       self.interface.version,
                       self.interface.release),
         join(self.interface.isodir, iso),
         join(self.interface.isodir, iso)),
         verbose=True)
      
  
  def delete_isotree(self, set):
    expanded_set = splittree.parse_size(set)
    if expanded_set not in self.newsets_expanded:
      osutils.rm(join(self.interface.isodir, set), recursive=True, force=True)
    else:
      newset = self.newsets[self.newsets_expanded.index(expanded_set)]
      os.rename(join(self.interface.isodir, set),
                join(self.interface.isodir, newset))
      if newset in self.interface.r:
        self.interface.r.remove(newset) # don't create iso tree; it already exists
  
  def generate_isotree(self, set):
    osutils.mkdir(join(self.interface.isodir, set), parent=True)
    
    splitter = splittree.Timber(set, dosrc=self.interface.get_cvar('source-include'))
    splitter.product = self.interface.product
    splitter.unified_tree = self.interface.getSoftwareStore()
    splitter.unified_source_tree = self.interface.getSoftwareStore()
    splitter.split_tree = join(self.interface.isodir, set)
    splitter.difmt = self.interface.getLocalPath(L_DISCINFO, '.')
    splitter.pkgorder = join(self.interface.getMetadata(), 'pkgorder')
    
    splitter.compute_layout()
    splitter.cleanup()
    splitter.split_trees()
    splitter.split_rpms()
    splitter.split_srpms()
    
  def check_isotree(self, set): pass
