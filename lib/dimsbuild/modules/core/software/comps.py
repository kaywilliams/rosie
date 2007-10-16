import copy

from dims import listcompare
from dims import sortlib
from dims import xmllib

from dimsbuild.event     import Event
from dimsbuild.logging   import L0, L1
from dimsbuild.constants import BOOLEANS_TRUE, BOOLEANS_FALSE

API_VERSION = 5.0

HEADER_FORMAT = '<?xml version=\'%s\' encoding=\'%s\'?>'

TYPES = ['mandatory', 'optional', 'conditional', 'default']
KERNELS = ['kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
           'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
           'kernel-BOOT']

LOCALIZED = False # enable if you want all the various translations in the comps

class CompsEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'comps',
      provides = ['comps-file', 'required-packages', 'user-required-packages'],
      requires = ['anaconda-version', 'repos', 'base-repoid'],
      conditionally_requires = ['included-packages', 'excluded-packages'],
    )

    self.comps = Element('comps')
    self.header = HEADER_FORMAT % ('1.0', 'UTF-8')

    self.DATA = {
      'variables': ['fullname', 'cvars[\'anaconda-version\']',
                    'cvars[\'included-packages\']',
                    'cvars[\'excluded-packages\']'],
      'config':    ['.'],
      'input':     [],
      'output':    []
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.comps_supplied = \
      self.config.get('text()', None)

    if self.comps_supplied:
      xpath = '/distro/comps'

      self.io.setup_sync(self.mddir, id='comps.xml', xpaths=[xpath])

      # ensure exactly only one item returned above
      if len(self.io.list_output(what='comps.xml')) != 1:
        raise RuntimeError("The path specified at '%s' expands to multiple "
                           "items.  Only one comps file is allowed." % xpath)

    else:
      self.comps_out = self.mddir/'comps.xml'
      self.groupfiles = self._get_groupfiles()

      # track changes in repo/groupfile relationships
      self.DATA['variables'].append('groupfiles')

      # track file changes
      self.DATA['input'].extend([groupfile for repo,groupfile in
                                 self.groupfiles])

  def run(self):
    self.log(0, L0("processing components file"))

    self.io.clean_eventcache(all=True)

    if self.comps_supplied: # download comps file
      self.log(1, L1("using existing file '%s'" % self.comps_supplied))
      self.io.sync_input()

    else: # generate comps file
      self.log(1, L1("creating new file"))
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
      raise RuntimeError("Unable to find cached comps file at '%s'.  "
                         "Perhaps you are skipping comps before "
                         "it has been allowed to run once?" % self.cvars['comps-file'])

    # set required packages variable
    self.cvars['required-packages'] = \
      xmllib.tree.read(self.cvars['comps-file']).xpath('//packagereq/text()')


  #------ COMPS FILE GENERATION METHODS ------#
  def _get_groupfiles(self):
    "Get a list of all groupfiles in all repositories"
    groupfiles = []

    # add the base repo first
    repos = [self.cvars['repos'][self.cvars['base-repoid']]]

    # now add the rest of the repos
    for repo in self.cvars['repos'].values():
      if repo.id != self.cvars['base-repoid']:
        repos.append(repo)

    for repo in repos:
      groupfile = repo.datafiles.get('group', None)
      if groupfile:
        groupfiles.append((repo.id,
                           repo.ljoin(repo.repodata_path, 'repodata', groupfile)))

    return groupfiles

  def _generate_comps(self):
    "Generate a comps.xml from config and cvar data"
    self._validate_repoids()

    self._groupfiledata = {} # data from group files
    self._groups = {} # groups we're creating

    # build up groups dictionary
    for groupfileid, path in self.groupfiles:
      self._process_groupfile(path, groupfileid)

    # create group objects, add packages to them
    for groupid, data in self._groupfiledata.items():
      # if packages is empty, no group definition was found
      if not data['packages']:
        raise CompsError("unable to find group definition for '%s' in any groupfile" % groupid)
      self._groups[groupid] = CompsGroup(groupid, **data['attrs'])
      # add group's packages to packagelist
      for package in data['packages']:
        self._groups[groupid].packagelist.add(
          CompsPackage(**self._process_pkg_xml(package)))

    # add packages listed separately in config or included-packages cvar to core
    for pkg in self.config.xpath('include/package', []):
      self._groups['core'].packagelist.add(
        CompsPackage(**self._process_pkg_xml(pkg)))

    for pkgtup in (self.cvars['included-packages'] or []):
      if not isinstance(pkgtup, tuple):
        pkgtup = (pkgtup, 'mandatory', None, None)
      self._groups['core'].packagelist.add(CompsPackage(*pkgtup))

    # make sure a kernel package or equivalent exists
    if not self._groups['core'].packagelist.intersection(KERNELS):
      self._groups['core'].packagelist.add(
        CompsPackage('kernel', type='mandatory'))

    # remove excluded packages
    for pkg in self.config.xpath('exclude/package/text()', []) + \
               (self.cvars['excluded-packages'] or []):
      for group in self._groups.values():
        group.packagelist.discard(pkg)

    # create a category
    category = CompsCategory('Groups', name=self.fullname,
                             anaconda_version=self.cvars['anaconda-version'],
                             description='Groups in %s' % self.fullname,
                             display_order='99',
                             groups=sorted(self._groups.keys()))

    # add groups to comps
    for group in sorted(self._groups.values(), lambda x,y: cmp(x.id, y.id)):
      self.comps.append(group.toXml())
    # add category to comps
    self.comps.append(category.toXml())


  def _validate_repoids(self):
    "Ensure that the repoids listed actually are defined"
    for group in self.config.xpath('groups/group[@repoid]', []):
      repoid  = group.get('@repoid')
      groupid = group.get('text()')
      try:
        self.cvars['repos'][repoid]
      except KeyError:
        raise CompsError("group '%s' specifies an invalid repoid '%s'; relevant config element is:\n%s" % \
                         (groupid, repoid, group))

  def _process_pkg_xml(self, elem):
    "Convert a package in xml form into a package tuple"
    return dict(name     = elem.text,
                type     = elem.get('@type', 'mandatory'),
                requires = elem.get('@requires', None),
                default  = elem.get('@default', None))

  def _process_groupfile(self, groupfile, id=None):
    "Process a groupfile, adding the requested groups to the groups dict"
    try:
      tree = xmllib.tree.read(groupfile)
    except:
      raise CompsError("error reading file '%s'" % groupfile)

    if id == self.cvars['base-repoid']:
      self._update_group_content('core', tree)

    for groupid in self.config.xpath(
        'groups/group[not(@repoid) or @repoid="%s"]/text()' % id, []):
      self._update_group_content(groupid, tree)

  def _update_group_content(self, groupid, tree):
    "Add the contents of a group in an xml tree to the group dict"
    self._groupfiledata.setdefault(groupid, {})

    # add attributes if not already present
    if not self._groupfiledata[groupid].has_key('attrs'):
      if LOCALIZED: q = '//group[id/text()="%s"]/*' % groupid
      else:         q = '//group[id/text()="%s"]/*[not(@xml:lang)]' % groupid
      for attr in tree.xpath(q):
        # filtering these in XPath is annoying
        if attr.tag != 'packagelist' and attr.tag != 'id':
          self._groupfiledata[groupid].setdefault('attrs', {})[attr.tag] = attr.text

    # add packages
    for pkg in tree.xpath('//group[id/text()="%s"]/packagelist/packagereq' % groupid):
      self._groupfiledata[groupid].setdefault('packages', set()).add(pkg)


class CompsPackageSet(set):
  """A set object that allows the user to discard items based on equality (I'm
  not entirely sure how its done normally, but its not on equality"""
  def discard(self, item):
    for k in self:
      if k == item:
        self.remove(k)
        return

class CompsGroup(object):
  def __init__(self, id, name=None, description=None, default=None,
                     uservisible=None, biarchonly=None, packages=None):
    # name, description can be a string or a dictionary of lang, string pairs
    self.id          = id
    self.name        = name
    self.description = description
    self.default     = default
    self.uservisible = uservisible
    self.biarchonly  = biarchonly

    self.packagelist = CompsPackageSet(packages or [])

  def __str__(self): return str(self.toXml())

  def toXml(self):
    group = Element('group')
    Element('id', text=self.id, parent=group)

    # add possibly-localized values
    for attr in ['name', 'description']:
      val = getattr(self, attr)
      if val:
        if isinstance(val, dict):
          def sort_keys(k1, k2): # None > strings, strings sort normally
            if   k1 is None: return -1
            elif k2 is None: return 1
            else: return cmp(k1, k2)

          for lang in sorted(val.keys(), sort_keys):
            lval = val[lang]
            if lang is None:
              Element(attr, text=lval, parent=group)
            else:
              # I want to find the guy who created Clark notation and strangle him
              Element(attr, text=lval, parent=group,
                      attrs={'{http://www.w3.org/XML/1998/namespace}lang': lang},
                      nsmap={'xml': 'http://www.w3.org/XML/1998/namespace'})
        else:
          Element(attr, text=val, parent=group)
    # add non-localized values
    for attr in ['default', 'uservisible', 'biarchonly']:
      if getattr(self, attr):
        Element(attr, text=getattr(self, attr), parent=group)

    # add all packages
    packagelist = Element('packagelist', parent=group)
    for package in sorted(self.packagelist, lambda x,y: cmp(x.name, y.name)):
      packagelist.append(package.toXml())

    return group

class CompsPackage(object):
  def __init__(self, name, type=None, requires=None, default=None):
    self.name     = name
    self.type     = type
    self.requires = requires
    self.default  = default

  def __str__(self): return str(self.toXml())

  def __eq__(self, other):
    if isinstance(other, self.__class__):
      return self.name == other.name
    elif isinstance(other, str):
      return self.name == other
    else:
      raise TypeError

  def toXml(self):
    attrs = {}
    if self.type:     attrs['type']     = self.type
    if self.requires: attrs['requires'] = self.requires
    if self.default:  attrs['default']  = self.default
    return Element('packagereq', text=self.name, attrs=attrs)

class CompsCategory(object):
  def __init__(self, id, name=None, description=None, display_order=None,
                     groups=None, anaconda_version = '0'):
    self.id               = id
    self.name             = name
    self.description      = description
    self.display_order    = display_order
    self.groups           = groups
    self.anaconda_version = anaconda_version

  def __str__(self): return str(self.toXml())

  def toXml(self):
    if sortlib.dcompare(self.anaconda_version, '10.2.0.14-1') < 0:
      top = Element('grouphierarchy')
      cat = Element('category', parent=top)
      Element('name', parent=cat, text=self.id)
      sub = Element('subcategories', parent=cat)
    else:
      top = Element('category')
      Element('id', parent=top, text=self.id)
      if self.name:          Element('name', parent=top, text=self.name)
      if self.description:   Element('description',   parent=top, text=self.description)
      if self.display_order: Element('display_order', parent=top, text=self.display_order)
      sub = Element('grouplist', parent=top)

    for groupid in self.groups or []:
      sub.append(Element('groupid', text=groupid))

    return top



#------- FACTORY FUNCTIONS -------#
# convenience functions
Element  = xmllib.tree.Element
uElement = xmllib.tree.uElement

EVENTS = {'software': [CompsEvent]}

#------ ERRORS ------#
class CompsError(StandardError): pass
