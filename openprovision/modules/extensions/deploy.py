#
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

from openprovision.event     import Event

from openprovision.modules.shared import DeployEventMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['DeployEvent'],
  description = 'installs and updates a client using the published distribution',
)


class DeployEvent(DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'deploy',
      parentid = 'all',
      requires = ['web-path', 'repomd-file', 'published-distribution'],
    )

    self.DATA =  {
      'variables': [],
      'config':    [],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.webpath = self.cvars['web-path'] / 'os'
    self.repomdfile = self.cvars['repomd-file']
    self.kstext = self.cvars['kickstart-file'].read_text()

    DeployEventMixin.setup(self)

  def run(self):
    DeployEventMixin.run(self)

  def apply(self):
    self.io.clean_eventcache()

