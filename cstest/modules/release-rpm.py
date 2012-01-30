#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

from centosstudio.errors   import CentOSStudioError
from centosstudio.util     import pps
from centosstudio.util     import repo
from centosstudio.util     import rxml
from centosstudio.validate import InvalidConfigError
from centosstudio.util.pps.constants import TYPE_NOT_DIR

from cstest          import (BUILD_ROOT, TestBuild, EventTestCase, 
                            ModuleTestSuite)
from cstest.core     import make_core_suite
from cstest.mixins   import RpmBuildMixinTestCase, RpmCvarsTestCase


class ReleaseRpmEventTestCase(RpmBuildMixinTestCase, EventTestCase):
  moduleid = 'release-rpm'
  eventid  = 'release-rpm'

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    base = repo.getDefaultRepoById('base', distro=self.distro,
                                           version=self.version,
                                           arch=self.arch,
                                           include_baseurl=True,
                                           baseurl='http://www.centossolutions.com/mirrors/%s' % self.distro)
    base.update({'mirrorlist': None, 'gpgcheck': None})

    repos.append(base.toxml()) # don't overwrite gpgkey and gpgcheck defaults

    return repos

class Test_ReleaseRpmBuild(ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars1(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars2(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_OutputsGpgkeys(ReleaseRpmEventTestCase):
  "creates output when gpgcheck enabled"
  def _make_repos_config(self):
    return ReleaseRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless((self.event.SOFTWARE_STORE/'gpgkeys').findpaths(mindepth=1))
    expected = [ x.basename for x in self.event.cvars['gpgkeys'] ]
    expected.append('gpgkey.list')
    found = [ x.basename for x in
             (self.event.SOFTWARE_STORE/'gpgkeys').findpaths(mindepth=1,
                                                             type=TYPE_NOT_DIR)]
    self.failUnless(expected)
    self.failUnless(set(expected) == set(found))

class Test_RemovesGpgkeys(ReleaseRpmEventTestCase):
  "removes output when gpgcheck disabled"
  _conf = """<release-rpm>
    <updates gpgcheck='false'/>
  </release-rpm>"""

  def _make_repos_config(self):
    return ReleaseRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not (self.event.SOFTWARE_STORE/'gpgkeys').
                         findpaths())


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('release-rpm')

  suite.addTest(make_core_suite(ReleaseRpmEventTestCase, distro, version, arch))
  suite.addTest(Test_ReleaseRpmBuild(distro, version, arch))
  suite.addTest(Test_ReleaseRpmCvars1(distro, version, arch))
  suite.addTest(Test_ReleaseRpmCvars2(distro, version, arch))
  suite.addTest(Test_OutputsGpgkeys(distro, version, arch))
  suite.addTest(Test_RemovesGpgkeys(distro, version, arch))

  return suite
