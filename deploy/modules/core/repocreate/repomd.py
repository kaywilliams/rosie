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
from deploy.event          import Event
from deploy.modules.shared import RepomdMixin

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
      provides = ['os-content', 'treeinfo-checksums'],
      requires = ['rpms', 'rpmsdir', 'groupfile'],
      conditionally_requires = ['checked-rpms'],
    )
    self.publish_module = 'publish'

    self.DATA = {
      'variables': set(["cvars['rpms']", "cvars['rpmsdir']"]),
      'input':     set(),
      'output':    set(),
    }

    RepomdMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.publish_module = 'publish'

    RepomdMixin.setup(self)

    self.io.add_fpath(self.cvars['rpmsdir'], self.OUTPUT_DIR)

    self.groupfile = ( 
      self.cvars['%s-setup-options' % self.publish_module]['groupfile'])

    self.DATA['input'].add(self.groupfile)

    self.DATA['variables'].add('repomdfile') # provided by repomd mixin

  def run(self):
    (self.OUTPUT_DIR / self.cvars['rpmsdir'].basename).rm(force=True)
    self.io.process_files(link=True, text=None) 

    # run createrepo
    self.createrepo(self.OUTPUT_DIR,
                    groupfile=self.groupfile,
                    checksum=self.locals.L_CHECKSUM['type'])

  def apply(self):
    cvar = self.cvars.setdefault('treeinfo-checksums', set())
    cvar.add((self.OUTPUT_DIR, self.repomdfile.relpathfrom(self.OUTPUT_DIR)))
