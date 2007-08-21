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

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'comps',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['comps-file', 'required-packages', 'user-required-packages'],
    'requires': ['anaconda-version', 'local-repodata'],
    'conditional-requires': ['RPMS', 'input-repos-changed'],
  },
]

HOOK_MAPPING = {
#  'InitHook':     'init',
#  'ApplyoptHook': 'applyopt',
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
  
class CompsHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'comps.comps'
    
    self.interface = interface
    
    self.comps = Element('comps')
    self.header = HEADER_FORMAT % ('1.0', 'UTF-8')
    
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'config':    ['/distro/comps'],
      'input':     [],
      'output':    []
    }
    self.mddir = join(self.interface.METADATA_DIR, 'comps')
    self.mdfile = join(self.mddir, 'comps.md')
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    self.comps_supplied = self.interface.config.get('/distro/comps/use-existing/path/text()', None)

    if self.comps_supplied: 
      i,o = self.interface.setup_sync(xpaths=[('/distro/comps/use-existing/path',
                                               osutils.dirname(self.interface.config.file),
                                               self.mddir)])
      self.DATA['input'].extend(i)
      self.DATA['output'].extend(o) 

      #TODO remove after list_output is fixed
      for item in o:
        dest,src = item
        self.comps_out=dest
        break
      # TODO uncomment after list_output is fixed
      #self.initrd_out=self.interface.list_output( initrd_in )

    else: 
      self.comps_out = join(self.mddir, 'comps.xml')
      self.DATA['output'].append(self.comps_out)

  def clean(self):
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
   
  def check(self):
    # if the input repos change, we need to run
    return self.interface.cvars['input-repos-changed'] or \
           self.interface.test_diffs()

  def run(self):
    self.interface.log(0, "processing comps file")

    # delete prior comps file
    self.interface.remove_output(all=True)

    # create mddir, if needed
    if not exists(self.mddir): osutils.mkdir(self.mddir)

    if self.comps_supplied: # download comps file   
      self.interface.log(1, "using comps file '%s'" % self.comps_supplied)
      self.interface.sync_input()

    else: # generate comps file
      self.interface.log(1, "creating comps file")
      self.generate_comps()
      self.comps.write(self.comps_out)
      os.chmod(self.comps_out, 0644)

    # write metadata
    self.interface.write_metadata()
  
  def apply(self):
    if not exists(self.comps_out):
      raise RuntimeError, "Unable to find cached comps file at '%s'. Perhaps you are skipping the comps event before it has been allowed to run once?" % self.comps_out
    
    # set comps-file variable
    self.interface.cvars['comps-file'] = self.comps_out
    
    # set required packages variable
    reqpkgs = xmltree.read(self.interface.cvars['comps-file']).xpath('//packagereq/text()')
    self.interface.cvars['required-packages'] = reqpkgs

  
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
