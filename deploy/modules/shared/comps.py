# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# Copyright 2005 Duke University

import fnmatch
import hashlib
import re
import sys

from deploy.constants import KERNELS
from deploy.errors    import DeployEventError

from deploy.util import magic

from deploy.dlogging import L1

from yum.constants import *
try:
    from xml.etree import cElementTree
except ImportError:
    import cElementTree
iterparse = cElementTree.iterparse
from yum.Errors import CompsException
#FIXME - compsexception isn't caught ANYWHERE so it's pointless to raise it
# switch all compsexceptions to grouperrors after api break


class CompsSetupEventMixin:
  comps_setup_mixin_version = "1.00"

  def __init__(self):
    self.provides.update('user-required-packages', 'excluded-packages',
                         'user-required-groups')

    if not hasattr(self, 'DATA'): self.DATA = {'variables': set(),}

    self.DATA['variables'].update(['comps_setup_mixin_version'])

  def setup(self):
    if not self.diff.handlers: self.diff.setup(self.DATA)

    c = self.cvars
    self.user_required_packages = c.setdefault('user-required-packages', {})
    self.user_required_groups =   c.setdefault('user-required-groups', set())
    self.excluded_packages =      c.setdefault('excluded-packages', set())

    self.default_groupid = self.name

    self.DATA['variables'].update(['default_groupid'])


class CompsComposeEventMixin(CompsSetupEventMixin):
  comps_compose_mixin_version = "1.01"

  def __init__(self):
    CompsSetupEventMixin.__init__(self)
    self.conditionally_requires.update(['user-required-packages',
                                        'user-required-groups',
                                        'excluded-packages', 
                                        'rpmbuild-data',
                                        'repos'])
    self.provides.update(['%-setup-options' % self.publish_module,
                          'groupfile'])

    if not hasattr(self, 'DATA'): self.DATA = {'variables': set(),
                                               'output': set()}

    self.DATA['variables'].update(['comps_compose_mixin_version'])

  def setup(self):
    CompsSetupEventMixin.setup(self)

    self.rpmbuild_data = self.cvars.get('rpmbuild-data', {})

    self.compsfile = self.mddir/'comps.xml'
    # set this early for use by superclasses (e.g. test-publish)
    self.cvars.setdefault('%s-setup-options' % self.publish_module, 
                          {})['groupfile'] = self.compsfile

    self.repos = self.cvars.get('repos', {})
    self.groupfiles = self._get_groupfiles()
    self._generate_comps()

    # validate
    if not self.comps.all_packages:
      raise NoPackagesOrGroupsSpecifiedError()

    # hash comps file content for use in change tracking
    self.comps_hash = hashlib.sha224(self.comps.xml()).hexdigest()

    # track variable changes
    self.DATA['variables'].update(['type', 'comps_hash'])

  def run(self):
    # write comps.xml
    self.log(1, L1("writing comps.xml"))
    self.compsfile.write_text(self.comps.xml())
    self.compsfile.chmod(0644)
    self.DATA['output'].add(self.compsfile)


  #------ COMPS FILE GENERATION METHODS ------#
  def _get_groupfiles(self):
    "Get a list of repoid, groupfile tuples for all repositories"
    groupfiles = []

    for repo in self.repos.values():
      if repo.has_gz:
        key = 'group_gz'
      else:
        key = 'group'
      for gf in repo.datafiles.get(key, []):
        groupfiles.append((repo.id, repo.localurl/gf.href))

    return groupfiles

  def _generate_comps(self):
    "Generate a comps.xml from config and cvar data"
    self._validate_repoids()

    groupfiles = {}
    for id, path in self.groupfiles:
      try:
        fp = None
        if magic.match(path) == magic.FILE_TYPE_GZIP:
          import gzip
          fp = gzip.open(path)
        elif magic.match(path) == magic.FILE_TYPE_XZ:
          import lzma 
          fp = lzma.LZMAFile(path)
        else:
          fp = open(path)
        groupfiles.setdefault(id, Comps()).add(fp)
      finally:
        fp and fp.close()

    self.rpm_required = set()
    self.rpm_obsoletes = set()

    for v in self.rpmbuild_data.values():
      self.rpm_required.update(v.get('rpm-requires', []))
      self.rpm_obsoletes.update(v.get('rpm-obsoletes', []))

    self.comps = Comps()

    for group in self.user_required_groups:
      added = False
      for repoid, gf in groupfiles.items():
        if ( group.getxpath('@repoid', None) is None or
             group.getxpath('@repoid', None) == repoid ):
          if gf.has_group(group.text):
            self.comps.add_group(gf.return_group(group.text))
            # clear all optional packages out
            self.comps.return_group(group.text).optional_packages = {}
            added = True
      if not added:
        raise GroupNotFoundError(group.text)

    core_group = self.comps.add_core_group()

    # add user-required packages
    self.comps.add_packages(self.user_required_packages)

    # make sure a kernel package or equivalent exists for system repos
    if self.type == 'system':
      kfound = False
      for group in self.comps.groups:
        if set(group.packages).intersection(KERNELS):
          kfound = True
          kgroup = group
          break
      if not kfound:
        core_group.mandatory_packages['kernel'] = 1
        kgroup = core_group

      # conditionally add kernel-devel package
      kgroup.conditional_packages['kernel-devel'] = 'gcc'

      self.comps.add_group(core_group)

    # remove excluded packages
    for pkg in self.excluded_packages.union(self.rpm_obsoletes):
      self.comps.remove_package(pkg)

    # create a category
    category = Category()
    category.categoryid  = 'Groups'
    category.name        = self.fullname
    category.description = 'Groups in %s' % self.fullname

    # add groups
    for group in self.comps.groups:
      category._groups[group.groupid] = 1

    # add category to comps
    self.comps.add_category(category)

    # create an environment
    environment = Environment()
    environment.environmentid  = 'minimal'
    environment.displayorder   = '5'
    environment.name           = 'Minimal Install'
    environment.description    = 'Basic functionality.'

    # add groups
    for group in self.comps.groups:
      environment._groups[group.groupid] = 1

    # add environment to comps
    self.comps.add_environment(environment)

  def _validate_repoids(self):
    "Ensure that the repoids listed actually are defined"
    for group in [ x for x in self.user_required_groups 
                  if x.get('repoid', None) ]:
      rid = group.get('repoid')
      gid = group.text
      try:
        self.repos[rid]
      except KeyError:
        raise RepoidNotFoundError(gid, rid)

      if rid not in [ x for x,_ in self.groupfiles ]:
        raise RepoHasNoGroupfileError(gid, rid)


#------ ERRORS ------#
class NoPackagesOrGroupsSpecifiedError(DeployEventError):
  message = "No packages or groups specified"

class CompsError(DeployEventError): pass

class GroupNotFoundError(CompsError):
  message = "Group '%(group)s' not found in any groupfile"

class PackageNotFoundError(CompsError):
  message = "Package '%(package)s' not found in any repository"

class RepoidNotFoundError(CompsError):
  message = "Group '%(group)s' specifies nonexistant repoid '%(repoid)s'"

class RepoHasNoGroupfileError(CompsError):
  message = ( "Group '%(group)s' specifies repoid '%(repoid)s', which "
              "doesn't have a groupfile" )

#------ COMPS HELPER METHODS ------#

# to_unicode backported from yum.misc
def to_unicode(obj, encoding='utf-8', errors='replace'):
    ''' convert a 'str' to 'unicode' '''
    if isinstance(obj, basestring):
        if not isinstance(obj, unocide):
            obj = unicode(obj, encoding, errors)
    return obj

lang_attr = '{http://www.w3.org/XML/1998/namespace}lang'

def parse_boolean(strng):
    if BOOLEAN_STATES.has_key(strng.lower()):
        return BOOLEAN_STATES[strng.lower()]
    else:
        return False

def parse_number(strng):
    return int(strng)

class Group(object):
    def __init__(self, elem=None):
        self.user_visible = True
        self.default = False
        self.selected = False
        self.name = ""
        self.description = ""
        self.translated_name = {}
        self.translated_description = {}
        self.mandatory_packages = {}
        self.optional_packages = {}
        self.default_packages = {}
        self.conditional_packages = {}
        self.langonly = None ## what the hell is this?
        self.groupid = None
        self.display_order = 5
        self.installed = False
        self.toremove = False

        if elem:
            self.parse(elem)

    def __str__(self):
        return self.name

    def _packageiter(self):
        # Gah, FIXME: real iterator/class
        lst = self.mandatory_packages.keys() + \
              self.optional_packages.keys() + \
              self.default_packages.keys() + \
              self.conditional_packages.keys()

        return lst

    packages = property(_packageiter)

    def _expand_languages(self, lang):
        import gettext
        languages = [lang]

        if 'C' not in languages:
            languages.append('C')

        # now normalize and expand the languages
        nelangs = []
        for lang in languages:
            for nelang in gettext._expand_lang(lang):
                if nelang not in nelangs:
                    nelangs.append(nelang)
        return nelangs

    def nameByLang(self, lang):

        for langcode in self._expand_languages(lang):
            if self.translated_name.has_key(langcode):
                return to_unicode(self.translated_name[langcode])

        return to_unicode(self.name)


    def descriptionByLang(self, lang):
        for langcode in self._expand_languages(lang):
            if self.translated_description.has_key(langcode):
                return to_unicode(self.translated_description[langcode])
        return to_unicode(self.description)

    def parse(self, elem):
        for child in elem:

            if child.tag == 'id':
                myid = child.text
                if self.groupid is not None:
                    raise CompsException
                self.groupid = myid

            elif child.tag == 'name':
                text = child.text
                if text:
                    text = text.encode('utf8')

                lang = child.attrib.get(lang_attr)
                if lang:
                    self.translated_name[lang] = text
                else:
                    self.name = text


            elif child.tag == 'description':
                text = child.text
                if text:
                    text = text.encode('utf8')

                lang = child.attrib.get(lang_attr)
                if lang:
                    self.translated_description[lang] = text
                else:
                    if text:
                        self.description = text

            elif child.tag == 'uservisible':
                self.user_visible = parse_boolean(child.text)

            elif child.tag == 'display_order':
                self.display_order = parse_number(child.text)

            elif child.tag == 'default':
                self.default = parse_boolean(child.text)

            elif child.tag in ['langonly', 'lang_only']:
                text = child.text
                if self.langonly is not None:
                    raise CompsException
                self.langonly = text

            elif child.tag == 'packagelist':
                self.parse_package_list(child)

    def parse_package_list(self, packagelist_elem):
        for child in packagelist_elem:
            if child.tag == 'packagereq':
                genre = child.attrib.get('type')
                if not genre:
                    genre = u'mandatory'

                if genre not in ('mandatory', 'default', 'optional', 'conditional'):
                    # just ignore bad package lines
                    continue

                package = child.text
                if genre == 'mandatory':
                    self.mandatory_packages[package] = 1
                elif genre == 'default':
                    self.default_packages[package] = 1
                elif genre == 'optional':
                    self.optional_packages[package] = 1
                elif genre == 'conditional':
                    self.conditional_packages[package] = child.attrib.get('requires')



    def add(self, obj):
        """Add another group object to this object"""

        # we only need package lists and any translation that we don't already
        # have

        for pkg in obj.mandatory_packages:
            self.mandatory_packages[pkg] = 1
        for pkg in obj.default_packages:
            self.default_packages[pkg] = 1
        for pkg in obj.optional_packages:
            self.optional_packages[pkg] = 1
        for pkg in obj.conditional_packages:
            self.conditional_packages[pkg] = obj.conditional_packages[pkg]

        # Handle cases where a comps.xml without name & decription tags
        # has been setup first, so the name & decription for this object is blank.


        if self.name == '' and obj.name != '':
            self.name = obj.name

        if self.description == '' and obj.description != '':
            self.description = obj.description

        # name and description translations
        for lang in obj.translated_name:
            if not self.translated_name.has_key(lang):
                self.translated_name[lang] = obj.translated_name[lang]

        for lang in obj.translated_description:
            if not self.translated_description.has_key(lang):
                self.translated_description[lang] = obj.translated_description[lang]

    def add_package(self, package, genre='mandatory', requires=None, 
                    default=None):
      """add a package to the group"""
      if genre == 'mandatory':
        self.mandatory_packages[package] = 1
      elif genre == 'default':
        self.default_packages[package] = 1
      elif genre == 'optional':
        self.optional_packages[package] = 1
      elif genre == 'conditional':
        self.conditional_packages[package] = requires

    def remove_package(self, package):
      for d in [ self.mandatory_packages, self.optional_packages,
                 self.default_packages, self.conditional_packages ]:
        d.pop(package, None) # remove package if found

    def xml(self):
        """write out an xml stanza for the group object"""
        msg ="""
  <group>
   <id>%s</id>
   <default>%s</default>
   <uservisible>%s</uservisible>
   <display_order>%s</display_order>\n""" % (self.groupid, str(self.default),
                                  str(self.user_visible), self.display_order)

        if self.langonly:
            msg += """   <langonly>%s</langonly>""" % self.langonly

        msg +="""   <name>%s</name>\n""" % self.name
        for (lang, val) in self.translated_name.items():
            msg += """   <name xml:lang="%s">%s</name>\n""" % (lang, val)

        msg += """   <description>%s</description>\n""" % self.description
        for (lang, val) in self.translated_description.items():
            msg += """   <description xml:lang="%s">%s</description>\n""" % (lang, val)

        msg += """    <packagelist>\n"""
        for pkg in self.mandatory_packages.keys():
            msg += """      <packagereq type="mandatory">%s</packagereq>\n""" % pkg
        for pkg in self.default_packages.keys():
            msg += """      <packagereq type="default">%s</packagereq>\n""" % pkg
        for pkg in self.optional_packages.keys():
            msg += """      <packagereq type="optional">%s</packagereq>\n""" % pkg
        for (pkg, req) in self.conditional_packages.items():
            msg += """      <packagereq type="conditional" requires="%s">%s</packagereq>\n""" % (req, pkg)
        msg += """    </packagelist>\n"""
        msg += """  </group>"""

        return msg


class Category(object):
    def __init__(self, elem=None):
        self.name = ""
        self.categoryid = None
        self.description = ""
        self.translated_name = {}
        self.translated_description = {}
        self.display_order = 5
        self._groups = {}

        if elem:
            self.parse(elem)

    def __str__(self):
        return self.name

    def _groupiter(self):
        return self._groups.keys()

    groups = property(_groupiter)

    def parse(self, elem):
        for child in elem:
            if child.tag == 'id':
                myid = child.text
                if self.categoryid is not None:
                    raise CompsException
                self.categoryid = myid

            elif child.tag == 'name':
                text = child.text
                if text:
                    text = text.encode('utf8')

                lang = child.attrib.get(lang_attr)
                if lang:
                    self.translated_name[lang] = text
                else:
                    self.name = text

            elif child.tag == 'description':
                text = child.text
                if text:
                    text = text.encode('utf8')

                lang = child.attrib.get(lang_attr)
                if lang:
                    self.translated_description[lang] = text
                else:
                    self.description = text

            elif child.tag == 'grouplist':
                self.parse_group_list(child)

            elif child.tag == 'display_order':
                self.display_order = parse_number(child.text)

    def parse_group_list(self, grouplist_elem):
        for child in grouplist_elem:
            if child.tag == 'groupid':
                groupid = child.text
                self._groups[groupid] = 1

    def add(self, obj):
        """Add another category object to this object"""

        for grp in obj.groups:
            self._groups[grp] = 1

        # name and description translations
        for lang in obj.translated_name:
            if not self.translated_name.has_key(lang):
                self.translated_name[lang] = obj.translated_name[lang]

        for lang in obj.translated_description:
            if not self.translated_description.has_key(lang):
                self.translated_description[lang] = obj.translated_description[lang]

    def xml(self):
        """write out an xml stanza for the category object"""
        msg ="""
  <category>
   <id>%s</id>
   <display_order>%s</display_order>\n""" % (self.categoryid, self.display_order)

        msg +="""   <name>%s</name>\n""" % self.name
        for (lang, val) in self.translated_name.items():
            msg += """   <name xml:lang="%s">%s</name>\n""" % (lang, val)

        msg += """   <description>%s</description>\n""" % self.description
        for (lang, val) in self.translated_description.items():
            msg += """    <description xml:lang="%s">%s</description>\n""" % (lang, val)

        msg += """    <grouplist>\n"""
        for grp in self.groups:
            msg += """     <groupid>%s</groupid>\n""" % grp
        msg += """    </grouplist>\n"""
        msg += """  </category>\n"""

        return msg

class Environment(Category):
    def __init__(self, elem=None):
        self.name = ""
        self.environmentid = None
        self.description = ""
        self.translated_name = {}
        self.translated_description = {}
        self.display_order = 5
        self._groups = {}

        if elem:
            self.parse(elem)

    def parse(self, elem):
        for child in elem:
            if child.tag == 'id':
                myid = child.text
                if self.environmentid is not None:
                    raise CompsException
                self.environmentid = myid

            elif child.tag == 'name':
                text = child.text
                if text:
                    text = text.encode('utf8')

                lang = child.attrib.get(lang_attr)
                if lang:
                    self.translated_name[lang] = text
                else:
                    self.name = text

            elif child.tag == 'description':
                text = child.text
                if text:
                    text = text.encode('utf8')

                lang = child.attrib.get(lang_attr)
                if lang:
                    self.translated_description[lang] = text
                else:
                    self.description = text

            elif child.tag == 'grouplist':
                self.parse_group_list(child)

            elif child.tag == 'display_order':
                self.display_order = parse_number(child.text)

    def add(self, obj):
        """Add another environment object to this object"""

        for grp in obj.groups:
            self._groups[grp] = 1

        # name and description translations
        for lang in obj.translated_name:
            if not self.translated_name.has_key(lang):
                self.translated_name[lang] = obj.translated_name[lang]

        for lang in obj.translated_description:
            if not self.translated_description.has_key(lang):
                self.translated_description[lang] = obj.translated_description[lang]

    def xml(self):
        """write out an xml stanza for the environment object"""
        msg ="""
  <environment>
   <id>%s</id>
   <display_order>%s</display_order>\n""" % (self.environmentid, self.display_order)

        msg +="""   <name>%s</name>\n""" % self.name
        for (lang, val) in self.translated_name.items():
            msg += """   <name xml:lang="%s">%s</name>\n""" % (lang, val)

        msg += """   <description>%s</description>\n""" % self.description
        for (lang, val) in self.translated_description.items():
            msg += """    <description xml:lang="%s">%s</description>\n""" % (lang, val)

        msg += """    <grouplist>\n"""
        for grp in self.groups:
            msg += """     <groupid>%s</groupid>\n""" % grp
        msg += """    </grouplist>\n"""
        msg += """  </environment>\n"""

        return msg


class Comps(object):
    def __init__(self):
        self._groups = {}
        self._categories = {}
        self._environments = {}
        self.compscount = 0
        self.compiled = False # have groups been compiled into avail/installed
                              # lists, yet.

    @property
    def all_packages(self):
      packages = []
      for group in self.groups:
        packages.extend(group.packages)

      return packages

    def get_groups(self):
        grps = self._groups.values()
        grps.sort(key = lambda x: (x.display_order, x.groupid))
        return grps

    def get_categories(self):
        cats = self._categories.values()
        cats.sort(key = lambda x: (x.display_order, x.categoryid))
        return cats

    def get_environments(self):
        envs = self._environments.values()
        envs.sort(key = lambda x: (x.display_order, x.environmentid))
        return envs

    groups = property(get_groups)
    categories = property(get_categories)
    environments = property(get_environments)

    def has_group(self, grpid):
        exists = self.return_groups(grpid)

        if exists:
            return True

        return False

    def return_group(self, grpid):
        """Return the first group which matches"""
        grps = self.return_groups(grpid)
        if grps:
            return grps[0]

        return None

    def return_groups(self, group_pattern, case_sensitive=False):
        """return all groups which match either by glob or exact match"""
        returns = {}

        for item in group_pattern.split(','):
            item = item.strip()
            if self._groups.has_key(item):
                thisgroup = self._groups[item]
                returns[thisgroup.groupid] = thisgroup
                continue

            if case_sensitive:
                match = re.compile(fnmatch.translate(item)).match
            else:
                match = re.compile(fnmatch.translate(item), flags=re.I).match

            for group in self.groups:
                names = [ group.name, group.groupid ]
                names.extend(group.translated_name.values())
                for name in names:
                    if match(name):
                        returns[group.groupid] = group

        return returns.values()

    def add_group(self, group, groupid = None):
        '''creates a new group, adds to an existing group with the same \
           groupid, or adds to a existing group specified using a groupid'''
        if not groupid:
            groupid = group.groupid
        if self._groups.has_key(groupid):
            thatgroup = self._groups[groupid]
            thatgroup.add(group)
        else:
            self._groups[groupid] = group

    def add_core_group(self):
      if not self.return_group('core'):
        core_group             = Group()
        core_group.name        = 'Core'
        core_group.groupid     = 'core'
        core_group.description = 'Core Packages'
        core_group.default     = True
        self.add_group(core_group)

      return self.return_group('core')

    def add_user_required_group(self, group_id):
      if not self.return_group(group_id):
        user_required_group             = Group()
        user_required_group.name        = group_id
        user_required_group.groupid     = group_id
        user_required_group.description = "%s packages" % group_id
        user_required_group.default     = True
        self.add_group(user_required_group)

      return self.return_group(group_id)

    def add_category(self, category):
        if self._categories.has_key(category.categoryid):
            thatcat = self._categories[category.categoryid]
            thatcat.add(category)
        else:
            self._categories[category.categoryid] = category

    def add_environment(self, environment):
        if self._environments.has_key(environment.environmentid):
            thatenv = self._environment[environment.environmentid]
            thatenv.add(environment)
        else:
            self._environments[environment.environmentid] = environment

    def add(self, srcfile = None):
        if not srcfile:
            raise CompsException

        if type(srcfile) == type('str'):
            # srcfile is a filename string
            infile = open(srcfile, 'rt')
        else:
            # srcfile is a file object
            infile = srcfile

        self.compscount += 1
        self.compiled = False

        parser = iterparse(infile)
        try:
          try:
            for event, elem in parser:
              if elem.tag == "group":
                 group = Group(elem)
                 self.add_group(group)
              if elem.tag == "category":
                 category = Category(elem)
                 self.add_category(category)
              if elem.tag == "environment":
                 environment = Environment(elem)
                 self.add_environment(environment)
          except SyntaxError, e:
            raise CompsException, "comps file is empty/damaged"
        finally:
          del parser

    def add_packages(self, pkgdict):
      for p,g in pkgdict.items():
        self.add_package(p, g)

    def add_package(self, package, groupid):
      group = (self.return_group(groupid) or
               self.add_user_required_group(groupid))
      group.mandatory_packages[package] = 1

    def remove_package(self, package):
      for group in self.groups:
        for l in [ group.mandatory_packages, group.optional_packages,
                   group.default_packages, group.conditional_packages ]:
          for pkgname in fnmatch.filter(l, package):
            del l[pkgname] 

    def compile(self, pkgtuplist):
        """ compile the groups into installed/available groups """

        # convert the tuple list to a simple dict of pkgnames
        inst_pkg_names = {}
        for (n,a,e,v,r) in pkgtuplist:
            inst_pkg_names[n] = 1


        for group in self.groups:
            # if there are mandatory packages in the group, then make sure
            # they're all installed.  if any are missing, then the group
            # isn't installed.
            if len(group.mandatory_packages) > 0:
                group.installed = True
                for pkgname in group.mandatory_packages:
                    if not inst_pkg_names.has_key(pkgname):
                        group.installed = False
                        break
            # if it doesn't have any of those then see if it has ANY of the
            # optional/default packages installed.
            # If so - then the group is installed
            else:
                check_pkgs = group.optional_packages.keys() + group.default_packages.keys() + group.conditional_packages.keys()
                group.installed = False
                for pkgname in check_pkgs:
                    if inst_pkg_names.has_key(pkgname):
                        group.installed = True
                        break

        self.compiled = True

    def xml(self):
        """returns the xml of the comps files in this class, merged"""

        if not self._groups and not self._categories and not self._environments:
            return ""

        msg = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE comps PUBLIC "-//Red Hat, Inc.//DTD Comps info//EN" "comps.dtd">
<comps>
"""

        for g in self.get_groups():
            msg += g.xml()
        for c in self.get_categories():
            msg += c.xml()
        for e in self.get_environments():
            msg += e.xml()

        msg += """\n</comps>\n"""

        return msg
