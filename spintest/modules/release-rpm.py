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
from spintest          import BUILD_ROOT, EventTestCase, ModuleTestSuite
from spintest.core     import make_core_suite
from spintest.rpmbuild import RpmBuildMixinTestCase, RpmCvarsTestCase

class ReleaseRpmEventTestCase(RpmBuildMixinTestCase, EventTestCase):
  moduleid = 'release-rpm'
  eventid  = 'release-rpm'
  _conf = """<release-rpm enabled="true"/>"""

class Test_ReleaseRpmInputs(ReleaseRpmEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    ReleaseRpmEventTestCase.__init__(self, distro, version, arch, conf=conf)

    self.working_dir = BUILD_ROOT
    self._add_config(
      """
      <release-rpm enabled="true">
        <file>%(working-dir)s/file1</file>
        <eula include-in-firstboot="true">%(working-dir)s/eula.en_US</eula>
        <omf  destdir="/usr/share/omf">%(working-dir)s/omf1</omf>
        <html destdir="/usr/share/html">%(working-dir)s/html1</html>
        <doc  destdir="/usr/share/doc">%(working-dir)s/doc1</doc>
      </release-rpm>
      """ % {'working-dir': self.working_dir})
    self.file1 = self.working_dir / 'file1'
    self.eula  = self.working_dir / 'eula.en_US'
    self.omf1  = self.working_dir / 'omf1'
    self.html1 = self.working_dir / 'html1'
    self.doc1  = self.working_dir / 'doc1'

  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.file1.touch()
    self.eula.touch()
    self.omf1.touch()
    self.html1.touch()
    self.doc1.touch()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ReleaseRpmEventTestCase.tearDown(self)
    self.file1.rm(force=True)
    self.eula.rm(force=True)
    self.omf1.rm(force=True)
    self.html1.rm(force=True)
    self.doc1.rm(force=True)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmBuild(ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars1(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmCvars2(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_RNotesExistence(ReleaseRpmEventTestCase):
  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ReleaseRpmEventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())
    rnotes = self.img_path.findpaths(glob='RELEASE-NOTES*')
    self.failIf(len(rnotes) == 0)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('release-rpm')

  suite.addTest(make_core_suite(ReleaseRpmEventTestCase, distro, version, arch))
  suite.addTest(Test_ReleaseRpmInputs(distro, version, arch))
  suite.addTest(Test_ReleaseRpmBuild(distro, version, arch))
  suite.addTest(Test_ReleaseRpmCvars1(distro, version, arch))
  suite.addTest(Test_ReleaseRpmCvars2(distro, version, arch))
  suite.addTest(Test_RNotesExistence(distro, version, arch))

  return suite
