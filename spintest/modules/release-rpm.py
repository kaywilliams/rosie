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
from spintest      import BUILD_ROOT, EventTestCase, ModuleTestSuite, config
from spintest.core import make_core_suite
from spintest.rpms import (RpmBuildMixinTestCase, InputFilesMixinTestCase,
                           RpmCvarsTestCase, ExtractMixin)

class ReleaseRpmEventTestCase(EventTestCase):
  moduleid = 'release-rpm'
  eventid  = 'release-rpm'
  _conf = """<release-rpm enabled="true"/>"""

class Test_ReleaseRpmInputs(InputFilesMixinTestCase, ReleaseRpmEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    ReleaseRpmEventTestCase.__init__(self, basedistro, arch, conf=conf)

    self.working_dir = BUILD_ROOT
    config.add_config_section(
      self.conf,
      """
      <release-rpm enabled="true">
        <release-files>
          <path>%s/file1</path>
        </release-files>
        <eula>
          <include-in-firstboot>true</include-in-firstboot>
          <path>%s/eula.en_US</path>
        </eula>
        <release-notes>
          <omf>
            <path dest="/usr/share/omf">%s/omf1</path>
          </omf>
          <html>
            <path dest="/usr/share/html">%s/html1</path>
          </html>
          <doc>
            <path dest="/usr/share/doc">%s/doc1</path>
          </doc>
        </release-notes>
        <yum-repos>
          <path>%s/repo1</path>
        </yum-repos>
      </release-rpm>
      """ % ((self.working_dir,)*6)
    )
    self.file1 = self.working_dir / 'file1'
    self.eula = self.working_dir / 'eula.en_US'
    self.omf1 = self.working_dir / 'omf1'
    self.html1 = self.working_dir / 'html1'
    self.doc1 = self.working_dir / 'doc1'
    self.repo1 = self.working_dir / 'repo1'

  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.file1.touch()
    self.eula.touch()
    self.omf1.touch()
    self.html1.touch()
    self.doc1.touch()
    self.repo1.touch()

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ReleaseRpmEventTestCase.tearDown(self)
    self.file1.rm(force=True)
    self.eula.rm(force=True)
    self.omf1.rm(force=True)
    self.html1.rm(force=True)
    self.doc1.rm(force=True)
    self.repo1.rm(force=True)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ReleaseRpmBuild(RpmBuildMixinTestCase, ReleaseRpmEventTestCase):
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

class Test_RNotesExistence(ExtractMixin, ReleaseRpmEventTestCase):
  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ReleaseRpmEventTestCase.tearDown(self)

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())
    rnotes = self.img_path.findpaths(glob='RELEASE-NOTES*')
    self.failIf(len(rnotes) == 0)

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('release-rpm')

  suite.addTest(make_core_suite(ReleaseRpmEventTestCase, basedistro, arch))
  suite.addTest(Test_ReleaseRpmInputs(basedistro, arch))
  suite.addTest(Test_ReleaseRpmBuild(basedistro, arch))
  suite.addTest(Test_ReleaseRpmCvars1(basedistro, arch))
  suite.addTest(Test_ReleaseRpmCvars2(basedistro, arch))
  suite.addTest(Test_RNotesExistence(basedistro, arch))

  return suite
