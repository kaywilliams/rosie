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
from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_core_suite

class RpmbuildRepoTestCase(EventTestCase):
  moduleid = 'rpmbuild-repo'
  eventid  = 'rpmbuild-repo'
  _type = 'package'

class Test_NoDefaults(RpmbuildRepoTestCase):
  "defaults are not added to rpmbuild repo list"
  def runTest(self):
    self.failIf('base'       in self.event.repos)
    self.failIf('everything' in self.event.repos)
    self.failIf('updates'    in self.event.repos)

class Test_Obsoletes(RpmbuildRepoTestCase):
  "rpm obsoletes removed from comps object"

  # add an obsolete to the config rpm
  _conf="""
  <config-rpms>
  <config-rpm id='test-config'>
  <obsoletes>test-package</obsoletes>
  </config-rpm>
  </config-rpms>
  """

  def setUp(self):
    RpmbuildRepoTestCase.setUp(self)

  def runTest(self):
    # execute predecessors
    self.execute_predecessors(self.event)

    # insert the test package into the comps core group
    core_group = self.event.cvars['comps-object'].return_group('core')
    core_group.add_package( package='test-package',
                            genre='mandatory',
                            requires=None,
                            default=None)

    # execute the event
    self.event.execute()

    # the test package should be removed from comps
    self.failIf('test-package' in self.event.cvars['comps-object'].all_packages)


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('rpmbuild-repo')

  suite.addTest(make_core_suite(RpmbuildRepoTestCase, os, version, arch))
  suite.addTest(Test_NoDefaults(os, version, arch))
  suite.addTest(Test_Obsoletes(os, version, arch))

  return suite
