from rendition import sortlib
from rendition import xmllib

from spin.event     import Event
from spin.logging   import L1
from spin.constants import BOOLEANS_TRUE, KERNELS

API_VERSION = 5.0
EVENTS = {'software': ['CompsEvent']}

class CompsEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'comps',
      provides = ['comps-file', 'required-packages', 'user-required-packages'],
      requires = ['anaconda-version', 'repos', 'base-repoid'],
      conditionally_requires = ['included-packages', 'excluded-packages'],
    )

    self.comps = Element('comps')

    self.DATA = {
      'variables': ['fullname', 'cvars[\'anaconda-version\']'],
      'config':    ['.'],
      'input':     [],
      'output':    []
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.include_localizations = \
      self.config.get('@include-localized-strings', 'False') in BOOLEANS_TRUE

    self.comps_supplied = self.config.get('text()', False)

    if self.comps_supplied:
      self.io.add_xpath('/distro/comps', self.mddir, id='comps.xml')

    else:
      self.comps_out = self.mddir/'comps.xml'
      self.groupfiles = self._get_groupfiles()

      # track changes in repo/groupfile relationships
      self.DATA['variables'].append('groupfiles')

      # track file changes
      self.DATA['input'].extend([groupfile for repo,groupfile in
                                 self.groupfiles])

    for i in ['included-packages', 'excluded-packages']:
      if not self.cvars.has_key(i): self.cvars[i] = []
      self.DATA['variables'].append('cvars[\'%s\']' % i)

  def run(self):
    self.io.clean_eventcache(all=True)

    if self.comps_supplied: # download comps file
      self.log(1, L1("using existing file '%s'" % self.comps_supplied))
      self.io.sync_input(cache=True)

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

    # set required packages variable
    try:
     self.cvars['required-packages'] = \
         xmllib.config.read(self.cvars['comps-file']).xpath('//packagereq/text()')
    except:
      pass # handled via verification below

    # set user required packages variable
    self.cvars['user-required-packages'] = \
         self.config.xpath('core/package/text()', [])

  # output verification
  def verify_comps_xpath(self):
    "user-specifed comps xpath query"
    self.verifier.failUnless(len(self.io.list_output(what='comps.xml')) < 2,
      "more than one user-specified comps file; using the first one only")

  def verify_cvar_comps_file(self):
    "cvars['comps-file'] exists"
    self.verifier.failUnless(self.cvars['comps-file'].exists(),
      "unable to find comps.xml file at '%s'" % self.cvars['comps-file'])


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
        groupfiles.append((repo.id, repo.localurl/'repodata'/groupfile))

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
    for gid, data in self._groupfiledata.items():
      # if packages is empty, no group definition was found
      if not data['packages']:
        raise CompsError("unable to find group definition for '%s' in any groupfile" % gid)
      self._groups[gid] = CompsGroup(gid, **data['attrs'])

      # add group's packagereqs to packagelist
      for pkg in data['packages']:
        self._groups[gid].packagelist.add(
          PackageReq(**self._dict_from_xml(pkg)))

      # add group's groupreqs to grouplist
      for grp in data['groups']:
        self._groups[gid].grouplist.add(
          GroupReq(grp.text))

    # add packages listed separately in config or included-packages cvar to core
    for pkg in self.config.xpath('core/package', []):
      self._groups['core'].packagelist.add(
        PackageReq(**self._dict_from_xml(pkg)))

    for pkgtup in (self.cvars['included-packages'] or []):
      if not isinstance(pkgtup, tuple):
        pkgtup = (pkgtup, 'mandatory', None, None)
      self._groups['core'].packagelist.add(PackageReq(*pkgtup))

    # make sure a kernel package or equivalent exists
    if not self._groups['core'].packagelist.intersection(KERNELS):
      self._groups['core'].packagelist.add(
        PackageReq('kernel', type='mandatory'))

    # remove excluded packages
    for pkg in ( self.config.xpath('exclude/package/text()', []) +
                 (list(self.cvars['excluded-packages']) or []) ):
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
    groups = []
    groups.extend(self.config.xpath('core/group[@repoid]', []))
    groups.extend(self.config.xpath('groups/group[@repoid]', []))

    repo_groupfiles = [ x for x,_ in self.groupfiles ]

    for group in groups:
      rid = group.get('@repoid')
      gid = group.get('text()')
      try:
        self.cvars['repos'][rid]
      except KeyError:
        raise CompsError("group '%s' specifies an invalid repoid '%s'; relevant config element is:\n%s" % \
                         (gid, rid, group))

      if rid not in repo_groupfiles:
        raise CompsError("group '%s' specifies a repoid '%s' that doesn't have its own groupfile" % \
                         (gid, rid))


  def _dict_from_xml(self, elem):
    "Convert a package in xml form into a package tuple"
    return dict(name     = elem.text,
                type     = elem.get('@type', None),
                requires = elem.get('@requires', None),
                default  = elem.get('@default', None))

  def _process_groupfile(self, groupfile, id=None):
    "Process a groupfile, adding the requested groups to the groups dict"
    try:
      tree = xmllib.config.read(groupfile)
    except:
      raise CompsError("error reading file '%s'" % groupfile)

    if id == self.cvars['base-repoid']:
      self._update_group_content('core', tree)

    for group in self.config.xpath(
      'core/group[not(@repoid) or @repoid="%s"]' % id, []):
      # I don't like the following hack - the goal is to allow users to have
      # groups that are installed by default on end machines; the core group
      # is 'special' to anaconda, and is thus always installed, so the packages
      # of these groups are included in core.  I'd rather create a separate
      # group, mark it as default True, and let users that want to mess with
      # kickstarts include it themselves (like the rest of the world does),
      # but the powers that be say otherwise
      self._update_group_content(group.text, tree, dgid='core')
    for group in self.config.xpath(
      'groups/group[not(@repoid) or @repoid="%s"]' % id, []):
        self._update_group_content(group.text, tree)

  def _update_group_content(self, gid, tree, dgid=None):
    "Add the contents of a group in an xml tree to the group dict"
    if not dgid: dgid = gid
    self._groupfiledata.setdefault(dgid, {})

    # add attributes if not already present
    if not self._groupfiledata[dgid].has_key('attrs'):
      self._groupfiledata[dgid]['attrs'] = {}
      if self.include_localizations:
        q = '//group[id/text()="%s"]/*' % gid
        namedict = self._groupfiledata[dgid]['attrs']['name'] = {}
        descdict = self._groupfiledata[dgid]['attrs']['description'] = {}
      else:
        q = '//group[id/text()="%s"]/*[not(@xml:lang)]' % gid

      for attr in tree.xpath(q):
        # filtering in XPath is annoying
        if attr.tag == 'name':
          if self.include_localizations:
            namedict[attr.get('@xml:lang')] = attr.text
          else:
            self._groupfiledata[dgid]['attrs']['name'] = attr.text
        elif attr.tag == 'description':
          if self.include_localizations:
            descdict[attr.get('@xml:lang')] = attr.text
          else:
            self._groupfiledata[dgid]['attrs']['description'] = attr.text
        elif attr.tag not in ['packagelist', 'grouplist', 'id']:
          self._groupfiledata[dgid]['attrs'][attr.tag] = attr.text

    # set the default value, if given
    #  * if default = true,    group.default = true
    #  * if default = false,   group.default = false
    #  * if default = default, group.default = value from groupfile
    #  * if default = None,    group.default = true
    default = self.config.get('groups/group[text()="%s"]/@default' % gid, None)
    if default:
      if default != 'default':
        self._groupfiledata[dgid]['attrs']['default'] = default
    else:
      self._groupfiledata[dgid]['attrs']['default'] = 'true'

    # add packages
    self._groupfiledata[dgid].setdefault('packages', set())
    for pkg in tree.xpath('//group[id/text()="%s"]/packagelist/packagereq' % gid, []):
      self._groupfiledata[dgid]['packages'].add(pkg)

    # add groups
    self._groupfiledata[dgid].setdefault('groups', set())
    for grp in tree.xpath('//group[id/text()="%s"]/grouplist/groupreq' % gid, []):
      self._groupfiledata[dgid]['groups'].add(grp)
      self._update_group_content(grp.text, tree)

class CompsReqSet(set):
  """A set object that does manipulation based on __eq__ rather than id()
  (I'm not entirely sure if this is how its done normally, but its definitely
  not on equality)"""
  def add(self, item):
    for k in self:
      if k == item:
        return
    set.add(self, item)

  def discard(self, item):
    for k in self:
      if k == item:
        self.remove(k)
        return

class CompsGroup(object):
  def __init__(self, id, name=None, description=None, default=None,
                     uservisible=None, biarchonly=None, packages=None,
                     groups=None):
    # name, description can be a string or a dictionary of lang, string pairs
    self.id          = id
    self.name        = name
    self.description = description
    self.default     = default
    self.uservisible = uservisible
    self.biarchonly  = biarchonly

    self.packagelist = CompsReqSet(packages or [])
    self.grouplist   = CompsReqSet(groups or [])

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
    if self.packagelist:
      packagelist = Element('packagelist', parent=group)
      for package in sorted(self.packagelist, lambda x,y: cmp(x.name, y.name)):
        packagelist.append(package.toXml())

    # add all groups
    if self.grouplist:
      grouplist = Element('grouplist', parent=group)
      for grp in sorted(self.grouplist, lambda x,y: cmp(x.name, y.name)):
        grouplist.append(grp.toXml())

    return group

class PackageReq(object):
  def __init__(self, name, type=None, requires=None, default=None):
    self.name     = name
    self.type     = type or 'mandatory'
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

class GroupReq(object):
  def __init__(self, name):
    self.name     = name

  def __str__(self): return str(self.toXml())

  def __eq__(self, other):
    if isinstance(other, self.__class__):
      return self.name == other.name
    elif isinstance(other, str):
      return self.name == other
    else:
      raise TypeError

  def toXml(self):
    return Element('groupreq', text=self.name)

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

    for gid in self.groups or []:
      sub.append(Element('groupid', text=gid))

    return top


#------- FACTORY FUNCTIONS -------#
# convenience functions
Element  = xmllib.config.Element
uElement = xmllib.config.uElement

#------ ERRORS ------#
class CompsError(StandardError): pass
