import copy
import os

from os.path import join, isfile, exists

from dims import listcompare
from dims import osutils
from dims import sortlib
from dims import xmltree

from dims.CacheManager import CacheManagerError
from dims.ConfigLib    import ConfigError

from event import EVENT_TYPE_PROC, EVENT_TYPE_MARK, EVENT_TYPE_MDLR

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'comps',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['comps.xml', 'required-packages', 'user-required-packages'],
    'requires': ['.discinfo', 'anaconda-version'],
    'conditional-requires': ['RPMS'],
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
  'CompsHook':    'comps',
}

HEADER_FORMAT = '<?xml version=\'%s\' encoding=\'%s\'?>'

TYPES = ['mandatory', 'optional', 'conditional', 'default']
KERNELS = ['kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
           'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
           'kernel-BOOT']


#------ HOOKS ------#
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'comps.init'
    
    self.interface = interface
  
  def run(self):
    parser = self.interface.getOptParser('build')
  
    parser.add_option('--with-comps',
                      default=None,
                      dest='with_comps',
                      metavar='COMPSFILE',
                      help='use COMPSFILE for the comps.xml instead of generating one')

class ApplyoptHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'comps.applyopt'
    
    self.interface = interface
  
  def run(self):
    if self.interface.options.with_comps is not None:
      self.interface.set_cvar('with-comps', self.interface.options.with_comps)

class CompsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'comps.comps'
    
    self.interface = interface
    
    # metadata and store comps file locations
    self.m_compsfile = join(self.interface.METADATA_DIR, 'comps.xml')
    self.s_compsfile = join(self.interface.SOFTWARE_STORE,
                            self.interface.product, 'base', 'comps.xml')
    
    self.comps = xmltree.Tree('comps')
    self.comps.setheader(HEADER_FORMAT % ('1.0', 'UTF-8'))
  
  def force(self):
    osutils.rm(self.m_compsfile, force=True)
    osutils.rm(self.s_compsfile, recursive=True, force=True)
  
  def run(self):
    if not self._test_runstatus(): return # check if we should be running
    
    self.interface.log(0, "computing required packages")
    
    groupfile = self.interface.get_cvar('with-comps',
                self.interface.config.get('//comps/use-existing/path/text()',
                None))
    if groupfile is not None:
      self.interface.log(1, "reading supplied groupfile '%s'" % groupfile)
      reqpkgs = xmltree.read(groupfile).get('//packagereq/text()')
    else:
      self.interface.log(1, "resolving required groups and packages")
      self.generate_comps()
      reqpkgs = self.comps.get('//packagereq/text()')
    
    if isfile(self.m_compsfile) and not self.interface.isForced('comps'):
      oldreqpkgs = xmltree.read(self.m_compsfile).get('//packagereq/text()')
    else:
      oldreqpkgs = []
    
    reqpkgs.sort()
    oldreqpkgs.sort()
    
    # test if required packages have changed
    old,new,_ = listcompare.compare(oldreqpkgs, reqpkgs)
    if len(old) > 0 or len(new) > 0:
      self.interface.log(1, "required packages have changed")
      if groupfile is not None:
        osutils.cp(groupfile, self.m_compsfile)
      else:
        self.interface.log(1, "writing comps.xml")
        self.comps.write(self.m_compsfile)
        os.chmod(self.m_compsfile, 0644)
      self.interface.set_cvar('comps-changed', True)
    else:
      self.interface.log(1, "required packages unchanged")
  
  def apply(self):
    compsfile = self.interface.get_cvar('comps-file') or self.m_compsfile
    if not exists(compsfile):
      raise RuntimeError, "Unable to find comps.xml at '%s'" % compsfile
    
    # copy groupfile
    if not self.interface.get_cvar('comps-file'):
      self.interface.set_cvar('comps-file', self.m_compsfile)
    osutils.mkdir(osutils.dirname(self.s_compsfile), parent=True)
    osutils.cp(self.interface.get_cvar('comps-file'), self.s_compsfile)
    
    # set required packages
    reqpkgs = xmltree.read(self.interface.get_cvar('comps-file')).get('//packagereq/text()')
    self.interface.set_cvar('required-packages', reqpkgs)
  
  def _test_runstatus(self):
    # if the input stores changes, we need to run
    # if there is no comps file in the ouput directory and one isn't otherwise
    # specified, we need to run
    return self.interface.isForced('comps') or \
           self.interface.get_cvar('with-comps') or \
           self.interface.get_cvar('input-store-changed') or \
           (not exists(self.m_compsfile) and not self.interface.get_cvar('comps-file'))
  
  #------ COMPS FILE GENERATION FUNCTIONS ------#
  def generate_comps(self):
    mapped, unmapped = self.__map_groups()
    groupfiles = self.__get_groupfiles()
    
    # create base distro group
    packages = []
    for pkg in self.interface.config.mget('//comps/create-new/include/package', []):
      pkgname = pkg.text
      pkgtype = pkg.iget('@type', 'mandatory')
      pkgrequires = pkg.iget('@requires', None)
      packages.append((pkgname, pkgtype, pkgrequires))
      
    for pkg in self.interface.get_cvar('included-packages', []):
      if type(pkg) == tuple:
        packages.append(pkg)
      else: 
        assert type(pkg) == str
        packages.append((pkg, 'mandatory', None))
    
    base = Group(self.interface.product, self.interface.fullname,
                 'This group includes packages specific to %s' % self.interface.fullname)
    if len(packages) > 0:
      self.interface.set_cvar('user-required-packages', [x[0] for x in packages])
      self.comps.getroot().append(base)
      for pkgname, pkgtype, pkgrequires in packages:
        self._add_group_package(pkgname, base, pkgrequires, type=pkgtype)
        
    processed = [] # processed groups
    
    # process groups
    for groupfileid, path in groupfiles:
      # read groupfile
      try:
        tree = xmltree.read(path)
      except ValueError, e:
        print e
        raise CompsError, "the file '%s' does not exist" % file
      
      # add the 'core' group of the base store
      if groupfileid == self.interface.getBaseStore():
        try:
          self._add_group_by_id('core', tree, mapped[groupfileid])
          processed.append('core')
        except IndexError:
          pass
          
      # process mapped groups - each MUST be processed or we raise an exception
      while len(mapped[groupfileid]) > 0:
        groupid = mapped[groupfileid].pop(0)
        if groupid in processed: continue # skip those we already processed
        default = self.interface.config.get('//main/groups/group[text()="%s"]/@default' % groupid, 'true')
        self._add_group_by_id(groupid, tree, mapped[groupfileid], default=default)
        processed.append(groupid)
        
      # process unmapped groups - these do not need to be processed at each step
      i = 0; j = len(unmapped)
      while i < j:
        groupid = unmapped[i]
        if groupid in processed:
          i += 1; continue
        try:
          group = tree.get('//group[id/text()="%s"]' % groupid)[0]
          default = self.interface.config.get('//main/groups/group[text()="%s"]/@default' % groupid, 'true')
          self._add_group_by_id(groupid, tree, unmapped, processed, default=default)
          processed.append(unmapped.pop(i))
          j = len(unmapped)
        except IndexError:
          i += 1
    
    if 'core' not in processed:
      raise CompsError, "The base store '%s' does not appear to define a 'core' group in any of its comps.xml files" % base_store
    
    # if any unmapped group wasn't processed, raise an exception
    if len(unmapped) > 0:
      raise ConfigError, "Unable to resolve all groups in available stores: missing %s" % unmapped['unmapped']
    
    # check to make sure a 'kernel' pacakge or equivalent exists - kinda icky
    allpkgs = self.comps.get('//packagereq/text()')
    found = False
    for kernel in KERNELS:
      if kernel in allpkgs:
        found = True; break
    if not found:
      # base is defined above, it is the base group for the repository
      if len(packages) == 0: self.comps.getroot().insert(0, base) # HAK HAK HAK
      self._add_group_package('kernel', base, type='mandatory')
    
    # exclude all package in self.exclude
    exclude = self.interface.config.mget('//comps/create-new/exclude/packages/text()') + \
              self.interface.get_cvar('excluded-packages', [])

    for pkg in exclude:
      matches = self.comps.get('//packagereq[text()="%s"]' % pkg)
      for match in matches:
        match.getparent().remove(match)
    
    # add category
    cat = Category('Groups', fullname=self.interface.fullname,
                             version=self.interface.get_cvar('anaconda-version'))
    self.comps.getroot().append(cat)
    for group in self.comps.getroot().get('//group/id/text()'):
      self._add_category_group(group, cat)
  
  def __map_groups(self):
    mapped = {}
    for store in self.interface.config.mget('//stores/*/store/@id'):
      mapped[store] = []
    unmapped = []
    
    for group in self.interface.config.mget('//main/groups/group'):
      store = group.attrib.get('store', None)
      if store is not None:
        try:
          mapped[store].append(group.text)
        except KeyError:
          raise ConfigError, "Invalid store '%s' specified in group %s" % (store, group)
      else:
        unmapped.append(group.text)
    
    return mapped, unmapped
  
  def __get_groupfiles(self):
    "Get a list of all groupfiles in all repositories"
    groupfiles = []
    
    for store in self.interface.config.mget('//stores/*/store/@id'):
      i,s,n,d,u,p = self.interface.getStoreInfo(store)
      d = d.lstrip('/') # remove absolute pathing on d
      
      repodatapath = self.interface.config.get('//stores/*/store[@id="%s"]/repodata-path/text()' % store, None)
      if repodatapath is not None:
        d = join(d, repodatapath) # TODO - this should accept absolute paths as well
      
      dest = join(self.interface.INPUT_STORE, i, d)
      osutils.mkdir(join(dest, 'repodata'), parent=True) # TODO allow this to be config'd?
      
      try:
        groupfile = self.interface.cache(join(d, 'repodata/repomd.xml'),
                                         prefix=i, username=u, password=p)
      except CacheManagerError:
        raise ConfigError, "The '%s' store does not appear to be valid; unable to get groupfile from '%s'" % (store, join(d, 'repodata/repomd.xml'))
      
      try:
        groupfile = xmltree.read(join(dest, 'repodata/repomd.xml')).get('//data[@type="group"]/location/@href')
        if len(groupfile) > 0:
          self.interface.cache(join(d, groupfile[0]), prefix=i)
        groupfiles.append((store, join(self.interface.INPUT_STORE, i, d, groupfile[0])))
      except IndexError:
        pass # this is ok, not all repositories have groupfiles
      
    return groupfiles
  
  def _add_group_package(self, package, group, requires=None, type='mandatory'):
    if type not in TYPES:
      raise ValueError, "Invalid type '%s', must be one of %s" % (type, TYPES)
    
    attrs = {}
    if requires is not None: attrs['requires'] = requires
    attrs['type'] = type
    
    packagelist = uElement('packagelist', parent=group)
    Element('packagereq', text=package, attrs=attrs, parent=packagelist)
    
  def _add_group_by_id(self, groupid, tree, toprocess, processed=[], default='true'):
    group = tree.get('//group[id/text()="%s"]' % groupid)[0]
    
    # append is destructive, so copy() it
    self.comps.getroot().append(copy.deepcopy(group))
    
    # replace the contents of the default element's text node
    self.comps.getroot().iget('group[id/text()="%s"]/default' % groupid).text = default
    
    # process any elements in the <grouplist> element
    groupreqs = tree.get('//group[id/text()="%s"]/grouplist/groupreq/text()' % groupid)
    for groupreq in groupreqs:
      if groupreq not in toprocess and groupreq not in processed:
        toprocess.append(groupreq)
  
  def _add_category_group(self, group, category, version='0'):
    if sortlib.dcompare(self.interface.get_cvar('anaconda-version'), '10.2.0.14-1') < 0:
      parent = category.iget('category/subcategories')
      Element('subcategory', parent=parent, text=group)
    else:
      parent = category.iget('grouplist')
      Element('groupid', parent=parent, text=group)


#------- FACTORY FUNCTIONS -------#
def Group(id, name, description='',
          default='true', uservisible='false', biarchonly='false'):
  group = Element('group')
  Element('id',          parent=group, text=id)
  Element('name',        parent=group, text=name)
  Element('description', parent=group, text=description)
  Element('default',     parent=group, text=default)
  Element('uservisible', parent=group, text=uservisible)
  Element('biarchonly',  parent=group, text=biarchonly)
  Element('packagelist', parent=group)
  return group

def Category(name, fullname='', version='0'):
  "Factory function for creating a category"
  if sortlib.dcompare(version, '10.2.0.14-1') < 0:
    top = Element('grouphierarchy')
    cat = Element('category', parent=top)
    uElement('name',          parent=cat, text='Groups')
    uElement('subcategories', parent=cat)
  else:
    top = Element('category')
    uElement('id',            parent=top, text=name)
    Element('name',           parent=top, text='Groups')
    Element('description',    parent=top, text='Groups in %s' % fullname)
    uElement('display_order', parent=top, text='99')
    uElement('grouplist',     parent=top)
  return top

def uElement(name, parent, **kwargs):
  "Gets the child of the parent named name, or creates it if it doesn't exist."
  elem = parent.iget(name, None)
  if elem is None:
    elem = xmltree.Element(name, parent=parent, **kwargs)
  return elem

Element = xmltree.Element # convenience function


#------ ERRORS ------#
class CompsError(StandardError): pass
