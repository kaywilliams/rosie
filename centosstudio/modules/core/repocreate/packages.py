#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

import cPickle
import hashlib 
import fnmatch

from centosstudio.util import magic

from centosstudio.constants import KERNELS
from centosstudio.errors    import assert_file_has_content, CentOSStudioError
from centosstudio.event     import Event
from centosstudio.cslogging import L1

from centosstudio.modules.shared import comps

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PackagesEvent', 'CompsEvent'],
  description = 'defines the required packages and groups for the system',
  group       = 'repocreate',
)

def is_enabled(*args, **kwargs):
  if kwargs['ptr'].type == 'component':
    return False
  else:
    return True

class PackagesEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'packages',
      parentid = 'setup-events',
      ptr = ptr,
      provides = ['comps-object', 'user-required-packages', 
                  'user-required-groups', 'excluded-packages'],
      requires = ['repos'],
      version = '1.01'
    )

    self.comps = None

    self.DATA = {
      'variables': ['fullname'],
      'config':    ['.'],
      'input':     [],
      'output':    []
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.groupfiles = self._get_groupfiles()
    self.pklfile = self.mddir/'packages.pkl'

    # track changes in repo/groupfile relationships
    self.DATA['variables'].append('groupfiles')

    # track file changes
    self.DATA['input'].extend([gf for _,gf in self.groupfiles])

    # set excluded packages and track
    self.cvars.setdefault('excluded-packages', [])
    self.cvars['excluded-packages'].extend(
        self.config.xpath('exclude/text()', []))
    self.DATA['variables'].append('cvars[\'excluded-packages\']')

  def run(self):
    self.io.clean_eventcache(all=True)

    self._generate_comps()
    fo = self.pklfile.open('wb')
    cPickle.dump(self.comps, fo, -1)
    self.DATA['output'].append(self.pklfile)
    fo.close()

  def apply(self):
    if not self.pklfile.exists(): return

    # read stored comps object 
    fo = self.pklfile.open('rb')
    self.cvars['comps-object'] = cPickle.load(fo)
    fo.close()

    # set user-*-* cvars
    self.cvars['user-required-packages'] = \
      self.config.xpath('package/text()', [])
    self.cvars['user-required-groups'] = \
      self.config.xpath('group/text()', []) 

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
    for cvar in  ['comps-object', 'user-required-packages', 
                  'user-required-groups', ]:
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

    self.comps = comps.Comps()

    if 'core' not in self.config.xpath('group', []):
      self.comps.add_core_group()

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
      core_group.mandatory_packages[package.text] = 1

    # make sure a kernel package or equivalent exists for system solutions
    if self.type == 'system':
      kfound = False
      for group in self.comps.groups:
        if set(group.packages).intersection(KERNELS):
          kfound = True; break
      if not kfound:
        core_group.mandatory_packages['kernel'] = 1

      self.comps.add_group(core_group)

    # remove excluded packages
    for pkg in self.cvars['excluded-packages']:
      self.comps.remove_package(pkg)

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


class CompsEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'comps',
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['groupfile'],
      requires = ['repos'], #extended in Depsolver mixin
      conditionally_requires = [], # set in Depsolver Mixin
      version = '1.00'
    )

    if self.type == 'application':
      self.enabled = False
      return

    self.DATA = {
      'variables': [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.compsfile = self.mddir/'comps.xml'

    # track changes to comps file content
    self.comps_hash = hashlib.sha224(
                      self.cvars['comps-object'].xml()).hexdigest()
    self.DATA['variables'].append('comps_hash')

  def run(self):
    # write comps.xml
    self.log(1, L1("writing comps.xml"))
    self.compsfile.write_text(self.cvars['comps-object'].xml())
    self.compsfile.chmod(0644)
    self.DATA['output'].append(self.compsfile)

  def apply(self):
    # set groupfile cvars
    self.cvars['groupfile'] = self.compsfile
    assert_file_has_content(self.cvars['groupfile'])

  def verify_cvar_comps_file(self):
    "cvars['groupfile'] exists"
    self.verifier.failUnless(self.cvars['groupfile'].exists(),
      "unable to find comps.xml file at '%s'" % self.cvars['groupfile'])


#------ ERRORS ------#
class CompsError(CentOSStudioError): pass

class GroupNotFoundError(CompsError):
  message = "Group '%(group)s' not found in any groupfile"

class PackageNotFoundError(CompsError):
  message = "Package '%(package)s' not found in any repository"

class RepoidNotFoundError(CompsError):
  message = "Group '%(group)s' specifies nonexistant repoid '%(repoid)s'"

class RepoHasNoGroupfileError(CompsError):
  message = ( "Group '%(group)s' specifies repoid '%(repoid)s', which "
              "doesn't have a groupfile" )
