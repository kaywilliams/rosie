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
import unittest

from deploy.errors import DeployError

from deploy.util import pps
from deploy.util import rxml

from dtest      import EventTestCase, ModuleTestSuite, _run_make
from dtest.core import make_core_suite


class GpgcheckEventTestCase(EventTestCase):
  moduleid = 'gpgcheck'
  eventid  = 'gpgcheck'
  _type = 'package'

  def _make_repos_config(self):
    repos = EventTestCase._make_repos_config(self)

    rxml.config.Element('repofile', text='shared/test-repos.repo', parent=repos)

    return repos


class Test_FailsOnUnsignedPackages(GpgcheckEventTestCase):
  "fails on unsigned packages"

  # create shared test repos
  _run_make(pps.path(__file__).dirname/'shared')

  # add an unsigned package
  _conf = """<packages>
    <package>package1</package>
  </packages>"""

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)


class Test_FailsIfKeyNotProvided(GpgcheckEventTestCase):
  "fails if key not provided"
  _type = 'system' # include packages from base repo
  _conf = """<packages>
    <package>kernel</package>
  </packages>"""

  def setUp(self):
    EventTestCase.setUp(self)

    # remove existing keys
    for gpgkey in  self.tb.definition.xpath("./repos/repo/gpgkey"):
      gpgkey.getparent().remove(gpgkey)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)


class Test_FailsOnBadKeyUrl(GpgcheckEventTestCase):
  "fails on bad key url"
  _type = 'system' # include packages from base repo
  _conf = """<packages>
    <package>kernel</package>
  </packages>"""

  def setUp(self):
    EventTestCase.setUp(self)

    # remove existing keys
    for gpgkey in  self.tb.definition.xpath("./repos/repo/gpgkey"):
      gpgkey.getparent().remove(gpgkey)

    # add bad key
    repo = self.tb.definition.getxpath("./repos/repo")
    rxml.config.Element('gpgkey', text='bad', parent=repo)

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, DeployError, 
                                       self.execute_predecessors, self.event)

def make_suite(os, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase, os, version, arch))
  suite.addTest(Test_FailsOnUnsignedPackages(os, version, arch))
  suite.addTest(Test_FailsIfKeyNotProvided(os, version, arch))
  suite.addTest(Test_FailsOnBadKeyUrl(os, version, arch))

  return suite
