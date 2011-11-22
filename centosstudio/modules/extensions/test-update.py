#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
import os

from centosstudio.callback  import BuildDepsolveCallback
from centosstudio.event     import Event, CLASS_META
from centosstudio.cslogging import L1, L2, L3
from centosstudio.util      import pps

from centosstudio.modules.shared import DeployEventMixin
from centosstudio.modules.shared.testpublish import TestPublishEventMixin

P = pps.path

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['TestUpdateEvent'],
  description = 'performs test updates on client systems',
)

class TestUpdatePublishEvent(TestPublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-update-publish',
      parentid = 'test-events',
      version = 1.0,
      requires = ['os-dir'],
      conditionally_requires = [ 'kickstart-file', 'config-release'],
      provides = ['test-webpath', 'test-repomdfile', 'test-kstext'],
    )

    self.localpath = self.get_local('/var/www/html/solutions/test-update')
    self.webpath = self.get_remote('solutions/test-update')

    TestPublishEventMixin.__init__(self)

  def clean(self):
    TestPublishEventMixin.clean(self)

  def setup(self):
    TestPublishEventMixin.setup(self)

  def run(self):
    TestPublishEventMixin.run(self)

  def apply(self):
    TestPublishEventMixin.apply(self)


class TestUpdateEvent(DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-update',
      parentid = 'test-events',
      requires = ['test-webpath', ], 
    )

    self.DATA =  {
      'config':    [], # populated by mixin
      'input':     [], # ditto
      'output':    [], # ditto
      'variables': [], # populated in setup
    }

  def setup(self):
    self.diff.setup(self.DATA)
    self.webpath = self.cvars['test-webpath'] 
    self.kstext = self.cvars['test-kstext']
    self.repomdfile = self.cvars['test-repomdfile']
    self.DATA['variables'].extend(['webpath', 'kstext', 'repomdfile'])
    DeployEventMixin.setup(self)

  def run(self):
    DeployEventMixin.run(self)

  def apply(self):
    self.io.clean_eventcache()
