import copy
import os

from os.path import join, isfile, exists

from dims import listcompare
from dims import osutils
from dims import sortlib
from dims import xmltree

from dims.CacheManager import CacheManagerError
from dims.configlib    import ConfigError

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MARK, EVENT_TYPE_MDLR
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MARK, EVENT_TYPE_MDLR

from dimsbuild.modules.lib import DiffMixin

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'comps',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['comps-file', 'comps-changed', 'required-packages', 'user-required-packages'],
    'requires': ['anaconda-version', 'local-repodata'],
    'conditional-requires': ['RPMS', 'input-repos-changed'],
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
  'CompsHook':    'comps',
  'ValidateHook': 'validate',
}

HEADER_FORMAT = '<?xml version=\'%s\' encoding=\'%s\'?>'

TYPES = ['mandatory', 'optional', 'conditional', 'default']
KERNELS = ['kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
           'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
           'kernel-BOOT']


#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'comps.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/comps', schemafile='comps.rng')
  
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
      self.interface.cvars['with-comps'] = self.interface.options.with_comps

class CompsHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'comps.comps'
    
    self.interface = interface
    
    # metadata and repo comps file locations
    self.s_compsfile = join(self.interface.METADATA_DIR, 'comps.xml')
    
    self.comps = Element('comps')
    self.header = HEADER_FORMAT % ('1.0', 'UTF-8')
    
    self.DATA = {
      'config': ['/distro/comps'],
      'output': [self.s_compsfile],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'comps.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def clean(self):
    osutils.rm(self.s_compsfile, force=True)
    self.clean_metadata()
  
  def check(self):
    # if the input repos change, we need to run
    # if there is no comps file in the ouput directory and one isn't otherwise
    # specified, we need to run
    return self.interface.cvars['with-comps'] or \
           self.interface.cvars['input-repos-changed'] or \
           (not exists(self.s_compsfile) and not self.interface.cvars['comps-file']) or \
           self.test_diffs()
  

  def run(self):
    self.interface.log(0, "computing required packages")
    
    groupfile = self.interface.cvars['with-comps'] or \
                self.interface.config.get('/distro/comps/use-existing/path/text()',
                None)
    if groupfile is not None:
      self.interface.log(1, "reading supplied groupfile '%s'" % groupfile)
      reqpkgs = xmltree.read(groupfile).xpath('//packagereq/text()')
    else:
      self.interface.log(1, "resolving required groups and packages")
      self.generate_comps()
      reqpkgs = self.comps.xpath('//packagereq/text()')
    
    if isfile(self.s_compsfile):
      oldreqpkgs = xmltree.read(self.s_compsfile).xpath('//packagereq/text()')
    else:
      oldreqpkgs = []
    
    reqpkgs.sort()
    oldreqpkgs.sort()
    
    # test if required packages have changed
    old,new,_ = listcompare.compare(oldreqpkgs, reqpkgs)
    if len(old) > 0 or len(new) > 0:
      self.interface.log(1, "required packages have changed")
      if groupfile is not None:
        osutils.cp(groupfile, self.s_compsfile)
      else:
        self.interface.log(1, "writing comps.xml")
        self.comps.write(self.s_compsfile)
        os.chmod(self.s_compsfile, 0644)
      self.interface.cvars['comps-changed'] = True
    else:
      self.interface.log(1, "required packages unchanged")
  
  def apply(self):
    compsfile = self.interface.cvars['comps-file'] or self.s_compsfile
    if not exists(compsfile):
      raise RuntimeError, "Unable to find comps.xml at '%s'" % compsfile
    
    # copy groupfile
    if not self.interface.cvars['comps-file']:
      self.interface.cvars['comps-file'] = self.s_compsfile
    osutils.mkdir(osutils.dirname(self.s_compsfile), parent=True)
    if self.interface.cvars['comps-file'] != self.s_compsfile:
      osutils.cp(self.interface.cvars['comps-file'], self.s_compsfile)
    
    # set required packages
    reqpkgs = xmltree.read(self.interface.cvars['comps-file']).xpath('//packagereq/text()')
    self.interface.cvars['required-packages'] = reqpkgs

    self.write_metadata()
  
  #------ COMPS FILE GENERATION FUNCTIONS ------#
  def generate_comps(self):
    mapped, unmapped = self.__map_groups()
    groupfiles = self.__get_groupfiles()
    
    # create base distro group
    packages = []
    for pkg in self.interface.config.xpath('/distro/comps/create-new/include/package', []):
      pkgname = pkg.get('text()')
      pkgtype = pkg.get('@type', 'mandatory')
      pkgrequires = pkg.get('@requires', None)
      packages.append((pkgname, pkgtype, pkgrequires))
      
    for pkg in (self.interface.cvars['included-packages'] or []):
      if type(pkg) == tuple:
        packages.append(pkg)
      else: 
        assert type(pkg) == str
        packages.append((pkg, 'mandatory', None))
    
    base = Group(self.interface.product, self.interface.fullname,
                 'This group includes packages specific to %s' % self.interface.fullname)
    if len(packages) > 0:
      self.interface.cvars['user-required-packages'] = [ x[0] for x in packages ]
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
      
      # add the 'core' group of the base repo
      if groupfileid == self.interface.getBaseRepoId():
        try:
          self._add_group_by_id('core', tree, mapped[groupfileid])
          processed.append('core')
        except IndexError:
          pass
          
      # process mapped groups - each MUST be processed or we raise an exception
      while len(mapped[groupfileid]) > 0:
        groupid = mapped[groupfileid].pop(0)
        if groupid in processed: continue # skip those we already processed
        default = self.interface.config.get('/distro/comps/create-new/groups/group[text()="%s"]/@default' % groupid, 'true')
        self._add_group_by_id(groupid, tree, mapped[groupfileid], default=default)
        processed.append(groupid)
        
      # process unmapped groups - these do not need to be processed at each step
      i = 0; j = len(unmapped)
      while i < j:
        groupid = unmapped[i]
        if groupid in processed:
          unmapped.pop(i)
          i += 1; continue
        try:
          group = tree.get('//group[id/text()="%s"]' % groupid)
          default = self.interface.config.get('/distro/comps/create-new/groups/group[text()="%s"]/@default' % groupid, 'true')
          self._add_group_by_id(groupid, tree, unmapped, processed, default=default)
          processed.append(unmapped.pop(i))
          j = len(unmapped)
        except IndexError:
          i += 1
    
    if 'core' not in processed:
      raise CompsError, "The base repo '%s' does not appear to define a 'core' group in any of its comps.xml files" % self.interface.getBaseRepoId()
    
    # if any unmapped group wasn't processed, raise an exception
    if len(unmapped) > 0:
      raise ConfigError, "Unable to resolve all groups in available repos: missing %s" % unmapped
    
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
    exclude = self.interface.config.xpath('/distro/comps/create-new/exclude/packages/text()', []) + \
              (self.interface.cvars['excluded-packages'] or [])

    for pkg in exclude:
      for match in self.comps.xpath('//packagereq[text()="%s"]' % pkg):
        match.getparent().remove(match)
    
    # add category
    cat = Category('Groups', fullname=self.interface.fullname,
                             version=self.interface.cvars['anaconda-version'])
    self.comps.getroot().append(cat)
    for group in self.comps.getroot().xpath('//group/id/text()'):
      self._add_category_group(group, cat)
  
  def __map_groups(self):
    mapped = {}
    for repo in self.interface.getAllRepos():
      mapped[repo.id] = []
    unmapped = []
    
    for group in self.interface.config.xpath('/distro/comps/create-new/groups/group', []):
      repo = group.attrib.get('repo', None)
      if repo is not None:
        try:
          mapped[repo].append(group.text)
        except KeyError:
          raise ConfigError, "Invalid repo '%s' specified in group %s" % (repo, group)
      else:
        unmapped.append(group.text)
    
    return mapped, unmapped
  
  def __get_groupfiles(self):
    "Get a list of all groupfiles in all repositories"
    groupfiles = []
    
    for repo in self.interface.getAllRepos():
      if repo.groupfile is not None:
        groupfiles.append((repo.id,
                           repo.ljoin(repo.repodata_path, 'repodata', repo.groupfile)))
      
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
    group = tree.get('//group[id/text()="%s"]' % groupid)
    if group is None:
      raise CompsError, "Group id '%s' not found in comps file" % groupid
    
    # append is destructive, so copy() it
    self.comps.getroot().append(copy.deepcopy(group))
    
    # replace the contents of the default element's text node
    self.comps.getroot().get('group[id/text()="%s"]/default' % groupid).text = default
    
    # process any elements in the <grouplist> element
    groupreqs = tree.xpath('//group[id/text()="%s"]/grouplist/groupreq/text()' % groupid)
    for groupreq in groupreqs:
      if groupreq not in toprocess and groupreq not in processed:
        toprocess.append(groupreq)
  
  def _add_category_group(self, group, category, version='0'):
    if sortlib.dcompare(self.interface.cvars['anaconda-version'], '10.2.0.14-1') < 0:
      parent = category.get('category/subcategories')
      Element('subcategory', parent=parent, text=group)
    else:
      parent = category.get('grouplist')
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

# convenience functions
Element  = xmltree.Element  
uElement = xmltree.uElement

#------ ERRORS ------#
class CompsError(StandardError): pass
