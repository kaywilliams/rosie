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
from systemstudio.util import repo
from systemstudio.util import rxml

from sstest import EventTestCase, ModuleTestSuite
from sstest.core import make_core_suite

from systemstudio.errors import SystemStudioError
from systemstudio.util.pps.constants import TYPE_NOT_DIR

class GpgcheckEventTestCase(EventTestCase):
  moduleid = 'gpgcheck'
  eventid = 'gpgcheck'

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    base = repo.getDefaultRepoById('base', distro=self.distro,
                                           version=self.version,
                                           arch=self.arch,
                                           include_baseurl=True,
                                           baseurl='http://www.renditionsoftware.com/mirrors/%s' % self.distro)
    base.update({'mirrorlist': None})

    repos.append(base.toxml()) # don't overwrite gpgkey and gpgcheck defaults

    return repos

  def _make_gpgcheck_config(self):
    gpgcheck = rxml.config.Element('gpgcheck', attrs={'enabled': 'true'})

    return gpgcheck

class Test_FailsOnUnsignedPackages(GpgcheckEventTestCase):
  "fails on unsigned packages"
  # package1 below is an unsigned package from shared test repo1
  _conf = """<packages>
    <package>package1</package>
  </packages>"""

  def _make_repos_config(self):
    repos = GpgcheckEventTestCase._make_repos_config(self)

    rxml.config.Element('repofile', text='shared/test-repos.repo', parent=repos)

    return repos

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(SystemStudioError, self.event)

class Test_FailsIfKeyNotProvided(GpgcheckEventTestCase):
  "fails if keys are not provided"

  # using repos_config from base EventTestCase class, which does
  # not include gpgkey definitions
  def _make_repos_config(self):
    return EventTestCase._make_repos_config(self)
 
  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(SystemStudioError, self.event)

class Test_CreatesOutput(GpgcheckEventTestCase):
  "creates output when gpgcheck enabled"
  def _make_repos_config(self):
    return GpgcheckEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(self.event.mddir.findpaths(mindepth=1, 
                                               nglob='gpgcheck.md'))

    expected = [ x.basename for x in self.event.io.list_output(what='gpgkeys') ]
    found = [ x.basename for x in
             (self.event.SOFTWARE_STORE/'gpgkeys').findpaths(mindepth=1,
                                                             type=TYPE_NOT_DIR)]
    self.failUnless(expected)
    self.failUnless(set(expected) == set(found))

class Test_RemovesOutput(GpgcheckEventTestCase):
  "removes output when gpgcheck disabled"
  # disable gpgcheck via /distribution/config/updates@gpgcheck
  _conf = """<config>
    <updates gpgcheck='false'/>
  </config>"""

  def _make_repos_config(self):
    return GpgcheckEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not self.event.mddir.findpaths(mindepth=1,
                                                   nglob='gpgcheck.md'))

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase, distro, version, arch))
  suite.addTest(Test_FailsOnUnsignedPackages(distro, version, arch))
  suite.addTest(Test_FailsIfKeyNotProvided(distro, version, arch))
  suite.addTest(Test_CreatesOutput(distro, version, arch))
  suite.addTest(Test_RemovesOutput(distro, version, arch))

  return suite
