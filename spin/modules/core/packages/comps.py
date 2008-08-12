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
from spin.errors    import assert_file_readable, SpinError
from spin.event     import Event
from spin.logging   import L1
from spin.validate  import InvalidConfigError

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['CompsEvent'],
  description = 'creates a comps.xml file',
  group       = 'packages',
)

class CompsEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'comps',
      parentid = 'packages',
      provides = ['comps-file', 'required-packages', 'user-required-packages'],
      requires = ['anaconda-version', 'repos'],
      conditionally_requires = ['comps-included-packages', 'comps-excluded-packages'],
    )

    self.comps = Element('comps')

    self.DATA = {
      'variables': ['fullname', 'cvars[\'anaconda-version\']'],
      'config':    ['.'],
      'input':     [],
      'output':    []
    }

  def validate(self):
    if ( not self.config.pathexists('text()') and
         not self.config.pathexists('group') and
         not self.config.pathexists('package') ):
      raise InvalidConfigError(self.config.getroot().file,
        "<%s> must contain either text or at least one <group> or "
        "<package> element" % self.id)

  def setup(self):
    self.diff.setup(self.DATA)

    self.include_localizations = \
      self.config.getbool('@include-localized-strings', 'False')

    self.comps_supplied = self.config.get('text()', False)

    if self.comps_supplied:
      assert_file_readable(self.config.getpath('.'))
      self.io.add_xpath('.', self.mddir, id='comps.xml')

    else:
      self.comps_out = self.mddir/'comps.xml'
      self.groupfiles = self._get_groupfiles()

      # track changes in repo/groupfile relationships
      self.DATA['variables'].append('groupfiles')

      # track file changes
      self.DATA['input'].extend([groupfile for repo,groupfile in
                                 self.groupfiles])

    for i in ['comps-included-packages', 'comps-excluded-packages']:
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

  def apply(self):
    self.io.clean_eventcache()
    # set comps-file control variable
    if self.comps_supplied:
      self.cvars['comps-file'] = self.io.list_output(what='comps.xml')[0]
    else:
      self.cvars['comps-file'] = self.comps_out

    # set required packages variable
    assert_file_readable(self.cvars['comps-file'])
    self.cvars['required-packages'] = \
       rxml.config.read(self.cvars['comps-file']).xpath('//packagereq/text()')

    # set user required packages variable
    self.cvars['user-required-packages'] = \
      self.config.xpath('package/text()', [])

  # output verification
  def verify_comps_xpath(self):
    "user-specified comps xpath query"
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

    for repo in self.cvars['repos'].values():
      for gf in repo.datafiles.get('group', []):
        groupfiles.append((repo.id, repo.localurl/gf))

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

    # add packages listed separately in config or included-packages cvar to core
    cfg_pkgs     = self.config.xpath('package', [])
    cvar_pkgtups = self.cvars['comps-included-packages'] or []

    # if we have packages, create a core group for them to reside in
    self._groups.setdefault('core',
      CompsGroup('core', name='core', description='autogenerated core group',
                         uservisible='true', biarchonly='false',
                         default='true', display_order='1',))

    for pkg in cfg_pkgs:
      self._groups['core'].packagelist.add(
        PackageReq(**self._dict_from_xml(pkg)))

    for pkgtup in cvar_pkgtups:
      if not isinstance(pkgtup, tuple):
        pkgtup = (pkgtup, 'mandatory', None, None)
      self._groups['core'].packagelist.add(PackageReq(*pkgtup))

    # make sure a kernel package or equivalent exists
    if not self._groups['core'].packagelist.intersection(KERNELS):
      self._groups['core'].packagelist.add(
        PackageReq('kernel', type='mandatory'))

    # remove excluded packages
    for pkg in ( self.config.xpath('exclude-package/text()', []) +
                 (list(self.cvars['comps-excluded-packages']) or []) ):
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
    assert_file_readable(groupfile)
    tree = rxml.config.read(groupfile)

    # add any other groups specified
    for group in self.config.xpath(
      'group[not(@repoid) or @repoid="%s"]' % id, []):
      self._update_group_content(group.text, tree)

  def _update_group_content(self, gid, tree):
    "Add the contents of a group in an xml tree to the group dict"
    G = self._groupfiledata.setdefault(gid, {})

    # add attributes if not already present
    if not G.has_key('attrs'):
      G['attrs'] = {}
      if self.include_localizations:
        q = '//group[id/text()="%s"]/*' % gid
        namedict = G['attrs']['name'] = {}
        descdict = G['attrs']['description'] = {}
      else:
        q = '//group[id/text()="%s"]/*[not(@xml:lang)]' % gid

      for attr in tree.xpath(q, []):
        # filtering in XPath is annoying
        if attr.tag == 'name':
          if self.include_localizations:
            namedict[attr.get('@xml:lang')] = attr.text
          else:
            G['attrs']['name'] = attr.text
        elif attr.tag == 'description':
          if self.include_localizations:
            descdict[attr.get('@xml:lang')] = attr.text
          else:
            G['attrs']['description'] = attr.text
        elif attr.tag not in ['packagelist', 'grouplist', 'id']:
          G['attrs'][attr.tag] = attr.text

    # set the default value, if given
    #  * if default = true,    group.default = true
    #  * if default = false,   group.default = false
    #  * if default = default, group.default = value from groupfile
    #  * if default = None,    group.default = true
    default = self.config.get('group[text()="%s"]/@default' % gid, None)
    if default:
      if default != 'default':
        G['attrs']['default'] = default
    else:
      G['attrs']['default'] = 'true'

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
    # name, description can be a string or a dictionary of lang, string pairs
    self.id            = id
    self.name          = name
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
    for attr in ['default', 'uservisible', 'biarchonly', 'display_order']:
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
