#
# Copyright (c) 2010
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

import fnmatch

from solutionstudio.util import magic

from solutionstudio.constants import KERNELS
from solutionstudio.errors    import assert_file_has_content, SolutionStudioError
from solutionstudio.event     import Event
from solutionstudio.logging   import L1

from solutionstudio.modules.shared import comps

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PackagesEvent'],
  description = 'defines the required packages and groups for the distribution',
  group       = 'repocreate',
)

class PackagesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'packages',
      parentid = 'repocreate',
      provides = ['groupfile', 'comps-object', 'comps-group-info',
                  'user-required-packages', 'user-required-groups',
                  'user-excluded-packages', 'all-packages'],
      requires = ['repos'],
      conditionally_requires = ['required-packages', 'excluded-packages'],
      version = '1.01'
    )

    self.comps = None
    self.app_gid = '%s-packages' % self.name

    self.DATA = {
      'variables': ['fullname'],
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
    self.DATA['input'].extend([gf for _,gf in self.groupfiles])

    for i in ['required-packages', 'excluded-packages']:
      self.cvars.setdefault(i, [])
      self.DATA['variables'].append('cvars[\'%s\']' % i)

  def run(self):
    self.io.clean_eventcache(all=True)

    self._generate_comps()
    self.comps_out.write_text(self.comps.xml())
    self.comps_out.chmod(0644)
    self.DATA['output'].append(self.comps_out)

  def apply(self):
    self.io.clean_eventcache()
    # set groupfile control variable
    self.cvars['groupfile'] = self.comps_out

    # set required packages variable
    assert_file_has_content(self.cvars['groupfile'])
    GF = comps.Comps()
    GF.add(self.cvars['groupfile'])

    self.cvars['comps-object'] = GF

    self.cvars.setdefault('comps-group-info', [])
    self.cvars.setdefault('all-packages', [])

    for group in GF.groups:
      self.cvars['all-packages'].extend(group.packages)

      gxml = self.config.get('group[text()="%s"]' % group.groupid, None)
      if gxml is not None:
        self.cvars['comps-group-info'].append((group.groupid,
                                         gxml.getbool('@default', True),
                                         gxml.getbool('@optional', False)))
      else:
        self.cvars['comps-group-info'].append((group.groupid, True, False))

    # set user-*-* cvars
    self.cvars['user-required-packages'] = \
      self.config.xpath('package/text()', [])
    self.cvars['user-required-groups'] = \
      self.config.xpath('group/text()', []) + [self.app_gid]
    self.cvars['user-excluded-packages'] = \
      self.config.xpath('exclude/text()', [])

    # set packages-* cvars
    self.cvars['packages-ignoremissing'] = \
      self.config.getbool('@ignoremissing', False)
    self.cvars['packages-default'] = \
      self.config.getbool('@default', False)
    self.cvars['packages-excludedocs'] = \
      self.config.getbool('@excludedocs', False)

  # output verification
  def verify_comps_xpath(self):
    "user-specified comps xpath query"
    self.verifier.failUnless(len(self.io.list_output(what='comps.xml')) < 2,
      "more than one user-specified comps file; using the first one only")

  def verify_cvar_comps_file(self):
    "cvars['groupfile'] exists"
    self.verifier.failUnless(self.cvars['groupfile'].exists(),
      "unable to find comps.xml file at '%s'" % self.cvars['groupfile'])

  def verify_cvars(self):
    "cvars set"
    for cvar in  ['groupfile', 'comps-object', 'comps-group-info',
                  'user-required-packages', 'user-required-groups',
                  'user-excluded-packages', 'all-packages']:
      self.verifier.failUnlessSet(cvar)


  #------ COMPS FILE GENERATION METHODS ------#
  def _get_groupfiles(self):
    "Get a list of repoid, groupfile tuples for all repositories"
    groupfiles = []

    for repo in self.cvars['repos'].values():
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
        else:
          fp = open(path)
        groupfiles.setdefault(id, comps.Comps()).add(fp)
      finally:
        fp and fp.close()

    allpkgs = [] # maintain a list of all packages in all repositories
    for repo in self.cvars['repos'].values():
      allpkgs.extend(repo.repocontent.return_pkgs('$name'))
    allpkgs = sorted(list(set(allpkgs))) # sort + uniq

    self.comps = comps.Comps()

    if 'comps' not in self.config.xpath('group', []):
      core_group             = comps.Group()
      core_group.name        = 'Core'
      core_group.groupid     = 'core'
      core_group.description = 'Core Packages'
      core_group.default     = True
      self.comps.add_group(core_group)

    # add groups
    for group in self.config.xpath('group', []):
      added = False
      for repoid, gf in groupfiles.items():
        if ( group.get('@repoid', None) is None or
             group.get('@repoid', None) == repoid ):
          if gf.has_group(group.text):
            self.comps.add_group(gf.return_group(group.text), 'core')
            # clear all optional packages out
            self.comps.return_group('core').optional_packages = {}
            added = True
      if not added:
        raise GroupNotFoundError(group.text)

    core_group = self.comps.return_group('core')

    # add packages
    for package in self.config.xpath('package', []):
      pkgs = fnmatch.filter(allpkgs, package.text)
      if len(pkgs) == 0:
        if self.config.getbool('@ignoremissing', 'False'):
          self.log(0, "Warning: no packages matching '%s' found in any "
                      "of the input repositories" % package.text)
        else:
          raise PackageNotFoundError(package.text)
      for pkgname in pkgs:
        core_group.mandatory_packages[pkgname] = 1

    # its a shame I have to replicate this code from comps.py
    for pkgtup in self.cvars['required-packages'] or []:
      if not isinstance(pkgtup, tuple):
        pkgtup = (pkgtup, 'mandatory', None, None)
      package, genre, requires, default = pkgtup
      if genre == 'mandatory':
        core_group.mandatory_packages[package] = 1
      elif genre == 'default':
        core_group.default_packages[package] = 1
      elif genre == 'optional':
        core_group.optional_packages[package] = 1
      elif genre == 'conditional':
        core_group.conditional_packages[package] = requires

    # make sure a kernel package or equivalent exists
    kfound = False
    for group in self.comps.groups:
      if set(group.packages).intersection(KERNELS):
        kfound = True; break
    if not kfound:
      core_group.mandatory_packages['kernel'] = 1

    self.comps.add_group(core_group)

    # remove excluded packages
    for pkg in ( self.config.xpath('exclude/text()', []) +
                 list(self.cvars['excluded-packages'] or []) ):
      for group in self.comps.groups:
        for l in [ group.mandatory_packages, group.optional_packages,
                   group.default_packages, group.conditional_packages ]:
          for pkgname in fnmatch.filter(l, pkg):
            del l[pkgname]

    # create a category
    category = comps.Category()
    category.categoryid  = 'Groups'
    category.name        = self.fullname
    category.description = 'Groups in %s' % self.fullname

    # add groups
    for group in self.comps.groups:
      category._groups[group.groupid] = 1

    # add category to comps
    self.comps.add_category(category)

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


#------ ERRORS ------#
class CompsError(SolutionStudioError): pass

class GroupNotFoundError(CompsError):
  message = "Group '%(group)s' not found in any groupfile"

class PackageNotFoundError(CompsError):
  message = "Package '%(package)s' not found in any repository"

class RepoidNotFoundError(CompsError):
  message = "Group '%(group)s' specifies nonexistant repoid '%(repoid)s'"

class RepoHasNoGroupfileError(CompsError):
  message = ( "Group '%(group)s' specifies repoid '%(repoid)s', which "
              "doesn't have a groupfile" )
