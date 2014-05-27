#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

from deploy.util import magic
from deploy.util import rxml 

from deploy.constants import KERNELS
from deploy.errors    import DeployEventError
from deploy.errors    import assert_file_has_content
from deploy.event     import Event

from deploy.modules.shared import comps, ShelveMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['PackagesEvent'],
    description = 'defines required packages and groups for the repository',
    group       = 'repocreate',
  )


class PackagesEvent(ShelveMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'packages',
      parentid = 'setup-events',
      ptr = ptr,
      provides = ['comps-object', 'user-required-packages', 
                  'excluded-packages'],
      conditionally_requires = ['repos'],
      version = '1.03'
    )

    self.comps = None

    self.DATA = {
      'variables': ['fullname'],
      'config':    ['.'],
      'input':     [],
      'output':    []
    }

    ShelveMixin.__init__(self)

  def validate(self):
    if (self.type == "system" and 
        len(self.config.xpath(['package', 'group'], [])) == 0):
      message = ("The definition specifies a system repository but no "
                 "packages or groups have been listed in the packages "
                 "element. Please specify groups and/or packages and try "
                 "again.")
      raise NoPackagesOrGroupsSpecifiedError(message=message)

  def setup(self):
    self.diff.setup(self.DATA)

    self.repos = self.cvars.get('repos', {})
    self.groupfiles = self._get_groupfiles()

    # track changes in repo/groupfile relationships
    self.DATA['variables'].append('groupfiles')

    # track changes in repo type
    self.DATA['variables'].append('type')

    # track file changes
    self.DATA['input'].extend([gf for _,gf in self.groupfiles])

    # set excluded packages
    self.cvars['excluded-packages'] = self.config.xpath('exclude/text()', [])

    # set user required packages
    self.cvars['user-required-packages'] = []
    for x in self.config.xpath('package/text()', []):
      if x.startswith('-'):
        self.cvars['excluded-packages'].append(x[1:])
      else:
        self.cvars['user-required-packages'].append(x)

  def run(self):
    self.io.clean_eventcache(all=True)

    self._generate_comps()
    self.shelve('comps', self.comps)

  def apply(self):
    if not self.unshelve('comps', None): return

    # read stored comps object 
    self.cvars['comps-object'] = self.unshelve('comps') 

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

  def verify_cvars(self):
    "cvars set"
    for cvar in  ['comps-object', 'user-required-packages']:
      self.verifier.failUnlessSet(cvar)


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
        else:
          fp = open(path)
        groupfiles.setdefault(id, comps.Comps()).add(fp)
      finally:
        fp and fp.close()

    self.comps = comps.Comps()

    if 'core' not in self.config.xpath('group', []):
      self.comps.add_core_group()

    for group in self.config.xpath('group', []):
      added = False
      for repoid, gf in groupfiles.items():
        if ( group.getxpath('@repoid', None) is None or
             group.getxpath('@repoid', None) == repoid ):
          if gf.has_group(group.text):
            self.comps.add_group(gf.return_group(group.text), 'core')
            # clear all optional packages out
            self.comps.return_group('core').optional_packages = {}
            added = True
      if not added:
        raise GroupNotFoundError(group.text)

    core_group = self.comps.return_group('core')

    # make sure a kernel package or equivalent exists for system repos
    if self.type == 'system':
      kfound = False
      for group in self.comps.groups:
        if set(group.packages).intersection(KERNELS):
          kfound = True; break
      if not kfound:
        core_group.mandatory_packages['kernel'] = 1

      # conditionally add kernel-devel package
      core_group.conditional_packages['kernel-devel'] = 'gcc'

      self.comps.add_group(core_group)

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

    # create an environment
    environment = comps.Environment()
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
    for group in self.config.xpath('group[@repoid]', []):
      rid = group.getxpath('@repoid')
      gid = group.getxpath('text()')
      try:
        self.repos[rid]
      except KeyError:
        raise RepoidNotFoundError(gid, rid)

      if rid not in [ x for x,_ in self.groupfiles ]:
        raise RepoHasNoGroupfileError(gid, rid)


#------ ERRORS ------#
class NoPackagesOrGroupsSpecifiedError(DeployEventError):
  message = "%(message)s"

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
