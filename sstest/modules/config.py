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
from solutionstudio.util import pps

from sbtest          import BUILD_ROOT, EventTestCase, ModuleTestSuite
from sbtest.core     import make_core_suite
from sbtest.rpmbuild import RpmBuildMixinTestCase, RpmCvarsTestCase

class ConfigRpmEventTestCase(RpmBuildMixinTestCase, EventTestCase):
  moduleid = 'config'
  eventid  = 'config'
  _conf = """<config enabled="true">
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config>"""

class Test_ConfigRpmInputs(ConfigRpmEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    ConfigRpmEventTestCase.__init__(self, distro, version, arch, conf=conf)

    self.working_dir = BUILD_ROOT
    self.file1 = pps.path('%s/file1' % self.working_dir)
    self.file2 = pps.path('%s/file2' % self.working_dir)
    self.dir1  = pps.path('%s/dir1'  % self.working_dir)
    self.file3 = pps.path('%s/file3' % self.dir1)
    self.script1 = pps.path('%s/script1' % self.working_dir)
    self.script2 = pps.path('%s/script2' % self.working_dir)

    self._add_config(
      """
      <config enabled="true">
        <files destdir="/etc/testdir">%(working-dir)s/file1</files>
        <files destdir="/etc/testdir" destname="file4">%(working-dir)s/file2</files>
        <files destdir="/etc/testdir" destname="file5" content="text">here is some text</files>
        <files destdir="/etc/testdir">%(working-dir)s/dir1</files>
        <!--<files destdir="/etc/testdir" destname="dir2" content="text">-->
        <script type="post">%(working-dir)s/script1</script>
        <script type="pre">%(working-dir)s/script1</script>
        <script type="preun">%(working-dir)s/script1</script>
        <script type="postun">%(working-dir)s/script1</script>
        <script type="verifyscript">%(working-dir)s/script1</script>
        <script type="post" content="text">echo post</script>
        <script type="pre" content="text">echo pre</script>
        <script type="preun" content="text">echo preun</script>
        <script type="postun" content="text">echo postun</script>
        <script type="verifyscript" content="text">echo verifyscript</script>
        <trigger package="bash" type="triggerin">%(working-dir)s/script1</trigger>
        <trigger package="bash" type="triggerun">%(working-dir)s/script1</trigger>
        <trigger package="python" type="triggerpostun" interpreter="/bin/python">%(working-dir)s/script1</trigger>
        <trigger package="bash" type="triggerin" content="text">echo triggerin</trigger>
        <trigger package="bash" type="triggerun" content="text">echo triggerun</trigger>
        <trigger package="python" type="triggerpostun" interpreter="/bin/python" content="text">print triggerpostun</trigger>
      </config>
      """ % {'working-dir': self.working_dir})

  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.file1.touch()
    self.file2.touch()
    self.dir1.mkdir()
    self.file3.touch()
    self.script1.touch()
    self.script2.touch()
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ConfigRpmEventTestCase.tearDown(self)
    self.file1.rm(force=True)
    self.file2.rm(force=True)
    self.script1.rm(force=True)
    self.script2.rm(force=True)

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmBuild(ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars1(RpmCvarsTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars2(RpmCvarsTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('config')

  suite.addTest(make_core_suite(ConfigRpmEventTestCase, distro, version, arch))
  suite.addTest(Test_ConfigRpmInputs(distro, version, arch))
  suite.addTest(Test_ConfigRpmBuild(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars1(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars2(distro, version, arch))

  return suite
