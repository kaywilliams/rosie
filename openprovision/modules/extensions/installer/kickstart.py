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

from openprovision.util  import pps
from openprovision.event import Event

from openprovision.modules.shared.kickstart import KickstartEventMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['KickstartEvent'],
  description = 'downloads a default kickstart file',
  group       = 'installer',
)

class KickstartEvent(KickstartEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'kickstart',
      parentid = 'installer',
      version = 1.02,
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content', 
                  'os-content'],
    )

    KickstartEventMixin.__init__(self)

    self.DATA = {
      'config':    ['.'],
      'variables': ['kickstart_mixin_version'],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    KickstartEventMixin.setup(self)

  # def run(self): # provided by KickstartEventMixin

  def apply(self):
    self.cvars['kickstart-file'] = self.ksfile
    self.cvars['ks-path'] = pps.path('/%s' % self.cvars['kickstart-file'].basename)

  def verify_cvars(self):
    "kickstart file exists"
    self.verifier.failUnlessExists(self.cvars['kickstart-file'])

