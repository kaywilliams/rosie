#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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
from repostudio.errors import CentOSStudioError

from repostudio.util import pps
from repostudio.util import repo
from repostudio.util import rxml

from rstest      import EventTestCase, ModuleTestSuite, _run_make
from rstest.core import make_core_suite


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
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_FailsIfKeyNotProvided(GpgcheckEventTestCase):
  "fails if key not provided"
  _type = 'system' # include packages from base and updates repo
  _conf = """<packages>
    <package>kernel</package>
  </packages>"""

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')
    base = repo.getDefaultRepoById('base', distro=self.distro,
           version=self.version, arch=self.arch, include_baseurl=True,
           baseurl='http://www.repostudio.org/mirrors/%s' % self.distro)
    # set gpgkeys to none
    base.update({'mirrorlist': None, 'gpgkey': None, 'gpgcheck': None,
                 'name': None,})
    repos.append(base.toxml())
    return repos

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(CentOSStudioError, self.event)


def make_suite(distro, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase, distro, version, arch))
  suite.addTest(Test_FailsOnUnsignedPackages(distro, version, arch))
  suite.addTest(Test_FailsIfKeyNotProvided(distro, version, arch))

  return suite
