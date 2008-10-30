#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
from rendition import rxml

from spin.constants import KERNELS
from spin.errors    import assert_file_has_content, SpinError
from spin.event     import Event
from spin.logging   import L1
from spin.validate  import InvalidConfigError

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PackagesEvent'],
  description = 'defines the required packages and groups for the appliance',
  group       = 'repocreate',
)

class PackagesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'packages',
      parentid = 'repocreate',
      provides = ['groupfile', 'all-packages', 'user-required-packages',
                  'user-required-groups', 'user-excluded-packages',
                  'comps-default-packages', 'comps-mandatory-packages',
                  'comps-optional-packages', 'comps-conditional-packages'],
      requires = ['anaconda-version', 'repos'],
      conditionally_requires = ['required-packages', 'excluded-packages'],
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

    self.comps_out = self.mddir/'comps.xml'
    self.groupfiles = self._get_groupfiles()

    # track changes in repo/groupfile relationships
    self.DATA['variables'].append('groupfiles')

    # track file changes
    self.DATA['input'].extend([groupfile for repo,groupfile in
                               self.groupfiles])

    for i in ['required-packages', 'excluded-packages']:
      self.cvars.setdefault(i, [])
      self.DATA['variables'].append('cvars[\'%s\']' % i)

  def run(self):
    self.io.clean_eventcache(all=True)

    self.log(1, L1("creating new file"))
    self._generate_comps()
    self.comps.write(self.comps_out)
    self.comps_out.chmod(0644)
    self.DATA['output'].append(self.comps_out)

  def apply(self):
    self.io.clean_eventcache()
    # set groupfile control variable
    self.cvars['groupfile'] = self.comps_out

    # set required packages variable
    assert_file_has_content(self.cvars['groupfile'])
    comps = rxml.config.read(self.cvars['groupfile'])
    self.cvars['all-packages'] = comps.xpath('//packagereq/text()')

    # set user-*-* cvars
    self.cvars['user-required-packages'] = \
      self.config.xpath('package/text()', [])
    self.cvars['user-required-groups'] = \
      self.config.xpath('group/text()', []) + ['%s-packages' % self.name]
    self.cvars['user-excluded-packages'] = \
      self.config.xpath('exclude/text()', [])

    # set comps-*-packages cvars
    default = []
    conditional = []
    for group in comps.xpath('group', []):
      if group.getbool('default/text()', 'True'):
        default.extend(group.xpath('packagelist/packagereq[@type="default"]/text()', []))
      for p in group.xpath('packagelist/packagereq[@type="conditional"]', []):
        conditional.append((p.text, p.get('@requires')))

    optional  = comps.xpath('//packagereq[@type="optional"]/text()',  [])
    mandatory = comps.xpath('//packagereq[@type="mandatory"]/text()', [])

    self.cvars['comps-default-packages']     = default
    self.cvars['comps-optional-packages']    = optional
    self.cvars['comps-mandatory-packages']   = mandatory
    self.cvars['comps-conditional-packages'] = conditional

  # output verification
  def verify_comps_xpath(self):
    "user-specified comps xpath query"
    self.verifier.failUnless(len(self.io.list_output(what='comps.xml')) < 2,
      "more than one user-specified comps file; using the first one only")

  def verify_cvar_comps_file(self):
    "cvars['groupfile'] exists"
    self.verifier.failUnless(self.cvars['groupfile'].exists(),
      "unable to find comps.xml file at '%s'" % self.cvars['groupfile'])


  #------ COMPS FILE GENERATION METHODS ------#
  def _get_groupfiles(self):
    "Get a list of all groupfiles in all repositories"
    groupfiles = []

    for repo in self.cvars['repos'].values():
      for gf in repo.datafiles.get('group', []):
        groupfiles.append((repo.id, repo.localurl/gf.href))

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
        raise GroupNotFoundError(gid)

      dg = self._groups.setdefault(gid, CompsGroup(gid, **data['attrs']))

      # add group's packagereqs to packagelist
      for pkg in data['packages']:
        dg.packagelist.add(PackageReq(**self._dict_from_xml(pkg)))

      # add group's groupreqs to grouplist
      for grp in data['groups']:
        dg.grouplist.add(GroupReq(grp.text))

    # add packages listed separately in config or included-packages
    # to new $NAME-packages group
    gid = '%s-packages' % self.name
    G = CompsGroup(gid,
                   description   = 'required %s appliance rpms' % self.fullname,
                   uservisible   = 'true',
                   biarchonly    = 'false',
                   default       = 'true',
                   display_order = '1')
    self._groups[gid] = G

    for pkg in self.config.xpath('package/text()', []):
      G.packagelist.add(PackageReq(pkg))

    for pkgtup in self.cvars['required-packages'] or []:
      if not isinstance(pkgtup, tuple):
        pkgtup = (pkgtup, 'mandatory', None, None)
      G.packagelist.add(PackageReq(*pkgtup))

    # make sure a kernel package or equivalent exists
    kfound = False
    for group in self._groups.values():
      if group.packagelist.intersection(KERNELS):
        kfound = True; break
    if not kfound:
      G.packagelist.add(PackageReq('kernel', 'mandatory'))

    # remove excluded packages
    for pkg in ( self.config.xpath('exclude/text()', []) +
                 list(self.cvars['excluded-packages'] or []) ):
      for group in self._groups.values():
        group.packagelist.discard(pkg)

    # create a category
    category = CompsCategory('Groups',
                             name          = self.fullname,
                             anaconda_version = self.cvars['anaconda-version'],
                             description   = 'Groups in %s' % self.fullname,
                             display_order = '99',
                             groups        = sorted(self._groups.keys()))

    # add groups to comps
    for group in sorted(self._groups.values(), lambda x,y: cmp(x.id, y.id)):
      self.comps.append(group.toXml())
    # add category to comps
    self.comps.append(category.toXml())


  def _validate_repoids(self):
    "Ensure that the repoids listed actually are defined"
    for group in self.config.xpath('group[@repoid]', []):
      rid = group.get('@repoid')
      gid = group.get('text()')
      try:
        self.cvars['repos'][rid]
      except KeyError:
        raise RepoidNotFoundError(gid, rid)

      if rid not in [ x for x,_ in self.groupfiles ]:
        raise RepoHasNoGroupfileError(gid, rid)


  def _dict_from_xml(self, elem):
    "Convert a package in xml form into a package tuple"
    return dict(name     = elem.text,
                type     = elem.get('@type', None),
                requires = elem.get('@requires', None),
                default  = elem.get('@default', None))

  def _process_groupfile(self, groupfile, id=None):
    "Process a groupfile, adding the requested groups to the groups dict"
    assert_file_has_content(groupfile)
    tree = rxml.config.read(groupfile)

    # add any other groups specified
    for group in self.config.xpath(
      'group[not(@repoid) or @repoid="%s"]' % id, []):
      self._update_group_content(group.text, tree)

  def _update_group_content(self, gid, tree):
    "Add the contents of a group in an xml tree to the group dict"
    G = self._groupfiledata.setdefault(gid, {})

    # add attributes if not already present
    G.setdefault('attrs', {})

    for attr in tree.xpath('//group[id/text()="%s"]/*[not(@xml:lang)]' % gid, []):
      if ( attr.tag not in ['packagelist', 'grouplist', 'id'] and
           not G['attrs'].has_key(attr.tag) ):
          G['attrs'][attr.tag] = attr.text

    # add packages
    G.setdefault('packages', set())
    for pkg in tree.xpath('//group[id/text()="%s"]/packagelist/packagereq' % gid, []):
      G['packages'].add(pkg)

    # add groups
    G.setdefault('groups', set())
    for grp in tree.xpath('//group[id/text()="%s"]/grouplist/groupreq' % gid, []):
      G['groups'].add(grp)
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
                     uservisible=None, biarchonly=None, display_order=None,
                     packages=None, groups=None):
    self.id           = id

    self.name          = name or id
    self.description   = description
    self.default       = default
    self.uservisible   = uservisible
    self.biarchonly    = biarchonly
    self.display_order = display_order
    self.packagelist = CompsReqSet(packages or [])
    self.grouplist   = CompsReqSet(groups or [])

  def __str__(self): return str(self.toXml())

  def toXml(self):
    group = Element('group')
    Element('id', text=self.id, parent=group)

    for attr in ['name', 'description', 'default', 'uservisible',
                 'biarchonly', 'display_order']:
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
      raise TypeError(type(other))

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
      raise TypeError(type(other))

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
    if self.anaconda_version < '10.2.0.14-1':
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
Element  = rxml.config.Element
uElement = rxml.config.uElement

#------ ERRORS ------#
class CompsError(SpinError): pass

class GroupNotFoundError(CompsError):
  message = "Group '%(group)s' not found in any groupfile"

class RepoidNotFoundError(CompsError):
  message = "Group '%(group)s' specifies nonexistant repoid '%(repoid)s'"

class RepoHasNoGroupfileError(CompsError):
  message = ( "Group '%(group)s' specifies repoid '%(repoid)s', which "
              "doesn't have a groupfile" )
