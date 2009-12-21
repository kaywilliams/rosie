#
# Copyright (c) 2007, 2008
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
from sbtest      import EventTestCase, ModuleTestSuite
from sbtest.core import make_core_suite

class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish-setup'

class PublishEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish'

  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(self.event.cvars['publish-path'])
    EventTestCase.tearDown(self)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('publish')

  # publish-setup
  suite.addTest(make_core_suite(PublishSetupEventTestCase, distro, version, arch))

  # publish
  suite.addTest(make_core_suite(PublishEventTestCase, distro, version, arch))

  return suite
