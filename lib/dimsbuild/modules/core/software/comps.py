import copy

from dims import listcompare
from dims import sortlib
from dims import xmltree

from dims.configlib import ConfigError

from dimsbuild.event     import Event
from dimsbuild.logging   import L0, L1
from dimsbuild.constants import BOOLEANS_TRUE, BOOLEANS_FALSE

API_VERSION = 5.0

HEADER_FORMAT = '<?xml version=\'%s\' encoding=\'%s\'?>'

TYPES = ['mandatory', 'optional', 'conditional', 'default']
KERNELS = ['kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
           'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
           'kernel-BOOT']


class CompsEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'comps',
      provides = ['comps-file', 'required-packages', 'user-required-packages'],
      requires = ['anaconda-version', 'repos', 'base-repoid'],
      conditionally_comes_after = ['RPMS'],
    )
    
    self.comps = Element('comps')
    self.header = HEADER_FORMAT % ('1.0', 'UTF-8')
    
    self.DATA = {
      'variables': ['fullname', 'cvars[\'anaconda-version\']'],
      'config':    ['/distro/comps'],
      'input':     [],
      'output':    []
    }
  
  def validate(self):
    self.validator.validate('/distro/comps', 'comps.rng')
  
  def setup(self):
    self.diff.setup(self.DATA)

    self.comps_supplied = \
      self.config.get('/distro/comps/text()', None)

    if self.comps_supplied: 
      xpath = '/distro/comps'

      self.io.setup_sync(self.mddir, id='comps.xml', xpaths=[xpath])

      # ensure exactly only one item returned above
      if len(self.io.list_output(what='comps.xml')) != 1: 
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
  
  def run(self):
    self.log(0, L0("processing comps file"))
    
    self.io.clean_eventcache(all=True)
    
    if self.comps_supplied: # download comps file   
      self.log(1, L1("using comps file '%s'" % self.comps_supplied))
      self.io.sync_input()
    
    else: # generate comps file
      self.log(1, L1("creating comps file"))
      self._generate_comps()
      self.comps.write(self.comps_out)
      self.comps_out.chmod(0644)
      self.DATA['output'].append(self.comps_out)
    
    # write metadata
    self.diff.write_metadata()
  
  def apply(self):
    self.io.clean_eventcache()
    # set comps-file control variable
    if self.comps_supplied: 
      self.cvars['comps-file'] = self.io.list_output(what='comps.xml')[0]
    else:
      self.cvars['comps-file'] = self.comps_out
    
    # verify comps-file exists
    if not self.cvars['comps-file'].exists():
      raise RuntimeError, "Unable to find cached comps file at '%s'. Perhaps you "\
      "are skipping the comps event before it has been allowed to run once?"\
      % self.cvars['comps-file']
        
    # set required packages variable
    self.cvars['required-packages'] = \
      xmltree.read(self.cvars['comps-file']).xpath('//packagereq/text()')
  
  
  #------ COMPS FILE GENERATION FUNCTIONS ------#
  def _generate_comps(self):
    mapped, unmapped = self.__map_groups()

    self.groups = {} # dict of grouptrees by groupid)
       
    ## build up groups dictionary
    for groupfileid, path in self.groupfiles:
      # read groupfile
      try:
        tree = xmltree.read(path)
      except ValueError, e:
        print e
        raise CompsError, "the file '%s' does not exist" % file
      
      # add the 'core' group of the base repo
      if groupfileid == self.cvars['base-repoid']:
        self.groups['core'] = self.__get_grouptree('core', tree, mapped[groupfileid])
      
      # process mapped groups - each MUST be processed or we raise an exception
      while len(mapped[groupfileid]) > 0:
        groupid = mapped[groupfileid].pop(0)
        if self.groups.has_key(groupid): continue
        self.groups[groupid] = self.__get_grouptree(groupid, tree, mapped[groupfileid])
   
      # process unmapped groups - these do not need to be processed at each step
      i = 0; j = len(unmapped)
      while i < j:
        groupid = unmapped[i]
        if self.groups.has_key(groupid):
          unmapped.pop(i)
          i += 1; continue
        try:
          group = tree.get('//group[id/text()="%s"]' % groupid)
          self.groups[groupid] = self.__get_grouptree(groupid, tree, unmapped) 
          j = len(unmapped)
        except IndexError:
          i += 1
 
    if not self.groups.has_key('core'):
      raise CompsError("The base repo '%s' does not appear "
                       "to define a 'core' group in any of its "
                       "comps.xml files" % self.cvars['base-repoid'])

    # if any unmapped group wasn't processed, raise an exception
    if len(unmapped) > 0:
      raise ConfigError, "Unable to resolve all groups in available repos: missing %s" % unmapped

    ### create comps file
    ## add core group
    self.comps.getroot().append(self.groups.pop('core'))

    ## add packages to core group
    # add packages from groups marked as 'core'
    core = [groupid for groupid in self.groups.keys() 
            if self.config.get('/distro/comps/groups/group[text()="%s"]/@core' \
            % groupid, 'true') in BOOLEANS_TRUE] 
    for groupid in sorted(core):
      self._add_group_pkgs(groupid, self.groups[groupid])

    # add packages listed separately in config or included-packages cvar
    packages = []
    for pkg in self.config.xpath('/distro/comps/include/package', []):
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
    
    core = self.comps.getroot().get('group[id/text()="core"]')

    if len(packages) > 0:
      self.cvars['user-required-packages'] = [ x[0] for x in packages ]
      self.comps.getroot().append(core)
      for pkgname, pkgtype, pkgrequires in packages:
        self._add_package(pkgname, core, pkgrequires, type=pkgtype)

    # check to make sure a 'kernel' pacakge or equivalent exists - kinda icky
    allpkgs = self.comps.get('//packagereq/text()')
    found = False
    for kernel in KERNELS:
      if kernel in allpkgs:
        found = True; break
    if not found:
      # base is defined above, it is the base group for the repository
      if len(packages) == 0: self.comps.getroot().insert(0, base) # HAK HAK HAK
      self._add_package('kernel', core, type='mandatory')

    ## add stand alone groups
    noncore = [groupid for groupid in self.groups.keys() 
               if self.config.get('/distro/comps/groups/group[text()="%s"]/@core' \
               % groupid, 'true') in BOOLEANS_FALSE] 
    for groupid in sorted(noncore):
      self._add_group(groupid, self.groups[groupid])
  
    ## exclude all package in self.exclude
    exclude = self.config.xpath('/distro/comps/exclude/packages/text()', []) + \
              (self.cvars['excluded-packages'] or [])

    for pkg in exclude:
      for match in self.comps.xpath('//packagereq[text()="%s"]' % pkg):
        match.getparent().remove(match)
    
    ## add category
    cat = Category('Groups', fullname=self.fullname,
                             version=self.cvars['anaconda-version'])
    self.comps.getroot().append(cat)
    for group in self.comps.getroot().xpath('//group/id/text()'):
      self._add_category(group, cat)
  
  def __map_groups(self):
    mapped = {}
    for repo in self.cvars['repos'].values():
      mapped[repo.id] = []
    unmapped = []
    
    for group in self.config.xpath('/distro/comps/groups/group', []):
      repo = group.attrib.get('repoid', None)
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
    
    for repo in self.cvars['repos'].values():
      groupfile = repo.datafiles.get('group', None)
      if groupfile is not None:
        groupfiles.append((repo.id,
                           repo.ljoin(repo.repodata_path, 'repodata', groupfile)))
      
    return groupfiles

  def __get_grouptree(self, groupid, tree, toprocess):
    "Get an xmltree object for the group, adds groupreqs to the toprocess list"
    grouptree = tree.get('//group[id/text()="%s"]' % groupid)
    if grouptree is None:
      raise CompsError, "Group id '%s' not found in comps file" % groupid

    # process any elements in the <grouplist> element
    groupreqs = grouptree.xpath('//grouplist/groupreq/text()')
    for groupreq in groupreqs:
      if groupreq not in toprocess and not self.groups.has_key(groupreq):
        toprocess.append(groupreq)

    return grouptree

  def _add_group(self, groupid, grouptree):
    self.comps.getroot().append(grouptree)
    default = self.config.get('/distro/comps/groups/group[text()="%s"]/@default' \
              % groupid, None)
    # replace the contents of the default element's text node
    if default is not None:
      self.comps.getroot().get('group[id/text()="%s"]/default' % groupid).text = default

  def _add_group_pkgs(self, groupid, grouptree):
    for package in grouptree.xpath('//group[id/text()="%s"]/packagelist/packagereq'\
                                     % groupid):
      self.comps.get('group[id/text()="core"]/packagelist').append(package)

  def _add_package(self, package, group, requires=None, type='mandatory'):
    if type not in TYPES:
      raise ValueError, "Invalid type '%s', must be one of %s" % (type, TYPES)
    
    attrs = {}
    if requires is not None: attrs['requires'] = requires
    attrs['type'] = type

    packagelist = uElement('packagelist', parent=group)
    Element('packagereq', text=package, attrs=attrs, parent=packagelist)
    
  def _add_category(self, group, category, version='0'):
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

EVENTS = {'SOFTWARE': [CompsEvent]}

#------ ERRORS ------#
class CompsError(StandardError): pass
