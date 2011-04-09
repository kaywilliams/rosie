
# Copyright (c) 2011
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

from systemstudio.event import Event

from systemstudio.modules.shared import RepomdMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['RepomdEvent'],
  description = 'creates repository metadata for pkglist RPMS',
  group       = 'repocreate',
)

class RepomdEvent(Event, RepomdMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'repomd',
      version = '1.03',
      parentid = 'repocreate',
      requires = ['rpms-directory', 'rpms'],
      provides = ['repodata-directory', 'treeinfo-checksums'],
      conditionally_requires = ['groupfile', 'checked-rpms'],
    )
    RepomdMixin.__init__(self)

    self.cvars['repodata-directory'] = self.SOFTWARE_STORE/'repodata'

    self.DATA = {
      'config':    ['.'],
      'variables': ['packagepath', 
                    'cvars[\'rpms\']', 
                    'cvars[\'rpms-directory\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    if self.cvars['groupfile']:
      self.DATA['input'].append(self.cvars['groupfile'])

  def run(self):
    # create temporary symlink to rpms-directory, deleted by clean_eventcache()
    self.cvars['rpms-directory'].symlink(self.SOFTWARE_STORE//self.packagepath)

    # run createrepo
    repo_files = self.createrepo(self.SOFTWARE_STORE, 
                                 groupfile=self.cvars['groupfile'],
                                 checksum=self.locals.L_CHECKSUM['type'])
    self.DATA['output'].extend(repo_files)

  def apply(self):
    self.io.clean_eventcache()
    self.cvars.setdefault('treeinfo-checksums', set()).add(
      (self.SOFTWARE_STORE, 'repodata/repomd.xml'))

  def verify_repodata_directory(self):
    self.verifier.failUnlessExists(self.cvars['repodata-directory'])
