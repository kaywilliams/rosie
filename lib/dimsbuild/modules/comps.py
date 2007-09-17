import copy

from dims import listcompare
from dims import sortlib
from dims import xmltree

from dims.configlib import ConfigError

from dimsbuild.event import Event, RepoMixin #!

API_VERSION = 5.0

HEADER_FORMAT = '<?xml version=\'%s\' encoding=\'%s\'?>'

TYPES = ['mandatory', 'optional', 'conditional', 'default']
KERNELS = ['kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
           'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
           'kernel-BOOT']


class CompsEvent(Event, RepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'comps',
      provides = ['comps-file', 'required-packages', 'user-required-packages'],
      requires = ['anaconda-version', 'local-repodata'],
      conditionally_requires = ['RPMS'],
    )
    
    self.comps = Element('comps')
    self.header = HEADER_FORMAT % ('1.0', 'UTF-8')
    
    self.DATA = {
      'variables': ['cvars[\'anaconda-version\']'],
      'config':    ['/distro/comps'],
      'input':     [],
      'output':    []
    }
    
    self.mdfile = self.get_mdfile()
    self.mddir = self.mdfile.dirname
  
  def _validate(self):
    self.validate('/distro/comps', 'comps.rng')
  
  def _setup(self):
    self.setup_diff(self.mdfile, self.DATA)

    self.comps_supplied = \
      self.config.get('/distro/comps/use-existing/path/text()', None)

    if self.comps_supplied: 
      xpath = '/distro/comps/use-existing/path'

      self.setup_sync(self.mddir, id='comps.xml', xpaths=[xpath])

      # ensure exactly only one item returned above
      if len(self.list_output(what='comps.xml')) != 1: 
        raise RuntimeError, "The path specified at '%s' expands to multiple "\
        "items. Only one comps file is allowed." % xpath 

    else:
      self.comps_out = self.mddir/'comps.xml'
      self.groupfiles = self.__get_groupfiles()

      # track changes in repo/groupfile relationships
      self.DATA['variables'].append('groupfiles') 

      # track file changes
      self.DATA['input'].extend([groupfile for repo,groupfile in
                                 self.groupfiles])
  
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()
  
  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "processing comps file")
    
    # delete prior comps file
    self.remove_output(all=True)
    
    if self.comps_supplied: # download comps file   
      self.log(1, "using comps file '%s'" % self.comps_supplied)
      self.sync_input()
    
    else: # generate comps file
      self.log(1, "creating comps file")
      self.generate_comps()
      self.comps.write(self.comps_out)
      self.comps_out.chmod(0644)
      self.DATA['output'].append(self.comps_out)
    
    # write metadata
    self.write_metadata()
  
  def _apply(self):
    # set comps-file control variable
    if self.comps_supplied: 
      self.cvars['comps-file'] = self.list_output(what='comps.xml')[0]
    else:
      self.cvars['comps-file'] = self.comps_out
    
    # verify comps-file exists
    if not self.cvars['comps-file'].exists():
      raise RuntimeError, "Unable to find cached comps file at '%s'. Perhaps you "\
      "are skipping the comps event before it has been allowed to run once?"\
      % self.comps_out
    
    # set required packages variable
    reqpkgs = xmltree.read(self.cvars['comps-file']).xpath('//packagereq/text()')
    self.cvars['required-packages'] = reqpkgs
  
  
  #------ COMPS FILE GENERATION FUNCTIONS ------#
  def generate_comps(self):
    mapped, unmapped = self.__map_groups()
    
    # create base distro group
    packages = []
    for pkg in self.config.xpath('/distro/comps/create-new/include/package', []):
      pkgname = pkg.get('text()')
      pkgtype = pkg.get('@type', 'mandatory')
      pkgrequires = pkg.get('@requires', None)
      packages.append((pkgname, pkgtype, pkgrequires))
      
    for pkg in (self.cvars['included-packages'] or []):
      if type(pkg) == tuple:
        packages.append(pkg)
      else:
        assert isinstance(pkg, str)
        packages.append((pkg, 'mandatory', None))
    
    base = Group(self.product, self.fullname,
                 'This group includes packages specific to %s' % self.fullname)
    if len(packages) > 0:
      self.cvars['user-required-packages'] = [ x[0] for x in packages ]
      self.comps.getroot().append(base)
      for pkgname, pkgtype, pkgrequires in packages:
        self._add_group_package(pkgname, base, pkgrequires, type=pkgtype)
    
    processed = [] # processed groups
    
    # process groups
    for groupfileid, path in self.groupfiles:
      # read groupfile
      try:
        tree = xmltree.read(path)
      except ValueError, e:
        print e
        raise CompsError, "the file '%s' does not exist" % file
      
      # add the 'core' group of the base repo
      if groupfileid == self.getBaseRepoId():
        try:
          self._add_group_by_id('core', tree, mapped[groupfileid])
          processed.append('core')
        except IndexError:
          pass
      
      # process mapped groups - each MUST be processed or we raise an exception
      while len(mapped[groupfileid]) > 0:
        groupid = mapped[groupfileid].pop(0)
        if groupid in processed: continue # skip those we already processed
        default = self.config.get('/distro/comps/create-new/groups/group[text()="%s"]/@default' % groupid, 'true')
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
          default = self.config.get('/distro/comps/create-new/groups/group[text()="%s"]/@default' % groupid, 'true')
          self._add_group_by_id(groupid, tree, unmapped, processed, default=default)
          processed.append(unmapped.pop(i))
          j = len(unmapped)
        except IndexError:
          i += 1
    
    if 'core' not in processed:
      raise CompsError, "The base repo '%s' does not appear to define a 'core' group in any of its comps.xml files" % self.getBaseRepoId()
    
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
    exclude = self.config.xpath('/distro/comps/create-new/exclude/packages/text()', []) + \
              (self.cvars['excluded-packages'] or [])

    for pkg in exclude:
      for match in self.comps.xpath('//packagereq[text()="%s"]' % pkg):
        match.getparent().remove(match)
    
    # add category
    cat = Category('Groups', fullname=self.fullname,
                             version=self.cvars['anaconda-version'])
    self.comps.getroot().append(cat)
    for group in self.comps.getroot().xpath('//group/id/text()'):
      self._add_category_group(group, cat)
  
  def __map_groups(self):
    mapped = {}
    for repo in self.getAllRepos():
      mapped[repo.id] = []
    unmapped = []
    
    for group in self.config.xpath('/distro/comps/create-new/groups/group', []):
      repo = group.attrib.get('repoid', None)
      print repo
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
    
    for repo in self.getAllRepos():
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
    if sortlib.dcompare(self.cvars['anaconda-version'], '10.2.0.14-1') < 0:
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

EVENTS = {'MAIN': [CompsEvent]}

#------ ERRORS ------#
class CompsError(StandardError): pass
