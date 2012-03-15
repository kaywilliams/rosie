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
from centosstudio.event          import Event
from centosstudio.modules.shared import RepomdMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['RepomdEvent'],
    description = 'creates repository metadata',
    group       = 'repocreate',
  )

class RepomdEvent(RepomdMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'repomd',
      version = 1.01,
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['os-content', 'repomd-file', 'treeinfo-checksums'],
      requires = ['pkglist', 'rpmsdir'],
      conditionally_requires = ['checked-rpms', 'groupfile'],
    )

    self.DATA = {
      'variables': ["cvars['rpms']", "cvars['rpmsdir']"],
      'input':     [],
      'output':    [],
    }

    RepomdMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    self.io.add_fpath(self.cvars['rpmsdir'], self.REPO_STORE)

    if self.cvars['groupfile']:
      self.DATA['input'].append(self.cvars['groupfile'])

    self.DATA['variables'].extend(['repomdfile']) # provided by repomd mixin

  def run(self):
    self.io.process_files(link=True, text=None) 

    # run createrepo
    repo_files = self.createrepo(self.REPO_STORE, 
                                 groupfile=self.cvars['groupfile'],
                                 checksum=self.locals.L_CHECKSUM['type'])
    self.DATA['output'].extend(repo_files)

  def apply(self):
    self.cvars['repomd-file'] = self.repomdfile
    self.cvars.setdefault('treeinfo-checksums', set()).add(
      (self.REPO_STORE, self.repomdfile.rstrip(self.REPO_STORE)))

  def verify_repodata_directory(self):
    self.verifier.failUnlessExists(self.cvars['repomd-file'])
