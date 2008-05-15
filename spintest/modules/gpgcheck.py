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
from rendition import xmllib

from spintest import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class GpgcheckEventTestCase(EventTestCase):
  moduleid = 'gpgcheck'
  eventid = 'gpgcheck'

  def _make_repos_config(self):
    repos = xmllib.config.Element('repos')

    for repoid in ['base', 'everything', 'updates']:
      # remove the mirrorlist for each repo
      repo = xmllib.config.Element('repo', attrs={'id': repoid}, parent=repos)
      xmllib.config.Element('mirrorlist', parent=repo)
      # don't delete the gpgkey/gpgcheck elements like other test cases

    return repos


class Test_GpgKeysNotProvided(GpgcheckEventTestCase):
  "raises RuntimeError when no keys are provided"
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

  def _make_repos_config(self):
    repos = xmllib.config.Element('repos')

    for repoid in ['base', 'everything', 'updates']:
      # remove the mirrorlist for each repo
      repo = xmllib.config.Element('repo', attrs={'id': repoid}, parent=repos)
      xmllib.config.Element('mirrorlist', parent=repo)
      xmllib.config.Element('gpgkey', parent=repo)
      # don't delete the gpgcheck elements like other test cases

    return repos

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase, distro, version, arch))
  suite.addTest(Test_GpgKeysNotProvided(distro, version, arch))

  return suite
