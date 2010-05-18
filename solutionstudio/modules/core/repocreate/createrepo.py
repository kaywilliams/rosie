#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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

from solutionstudio.event import Event

from solutionstudio.modules.shared import CreaterepoMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['CreaterepoEvent'],
  description = 'creates repository metadata for pkglist RPMS',
  group       = 'repocreate',
)

class CreaterepoEvent(Event, CreaterepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'createrepo',
      version = '0.1',
      parentid = 'repocreate',
      provides = ['rpms', 'rpms-directory', 'repodata-directory',
                  'treeinfo-checksums'],
      requires = ['cached-rpms'],
      conditionally_requires = ['groupfile', 'signed-rpms', 'gpgsign-public-key'],
    )
    CreaterepoMixin.__init__(self)

    self.cvars['repodata-directory'] = self.SOFTWARE_STORE/'repodata'

    self.DATA = {
      'config':    ['.'],
      'variables': ['packagepath'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.cvars['rpms-directory'] = self.SOFTWARE_STORE//self.packagepath

    if self.cvars['groupfile']:
      self.DATA['input'].append(self.cvars['groupfile'])

    if self.cvars['gpgsign-public-key']: # if we're signing rpms #!
      paths = self.cvars['signed-rpms']
    else:
      paths = self.cvars['cached-rpms']

    self.io.add_fpaths(paths, self.cvars['rpms-directory'], id='rpms')

  def run(self):
    self.io.sync_input(link=True)

    # remove all obsolete RPMs
    old_files = set(self.cvars['rpms-directory'].findpaths(mindepth=1, regex='.*\.rpm'))
    new_files = set(self.io.list_output(what='rpms'))
    for obsolete_file in old_files.difference(new_files):
      obsolete_file.rm(recursive=True, force=True)

    # run createrepo
    repo_files = self.createrepo(self.SOFTWARE_STORE, groupfile=self.cvars['groupfile'])
    self.DATA['output'].extend(repo_files)

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['rpms'] = self.io.list_output(what='rpms')
    self.cvars.setdefault('treeinfo-checksums', set()).add(
      (self.SOFTWARE_STORE, 'repodata/repomd.xml'))

  def verify_repodata_directory(self):
    self.verifier.failUnlessExists(self.cvars['repodata-directory'])
