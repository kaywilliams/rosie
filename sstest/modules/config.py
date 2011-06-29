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
from systemstudio.util     import pps
from systemstudio.util     import repo
from systemstudio.util     import rxml
from systemstudio.validate import InvalidConfigError
from systemstudio.util.pps.constants import TYPE_NOT_DIR

from sstest          import (BUILD_ROOT, TestBuild, EventTestCase, 
                            ModuleTestSuite)
from sstest.core     import make_core_suite
from sstest.rpmbuild import RpmBuildMixinTestCase, RpmCvarsTestCase

class ConfigEventTestCase(RpmBuildMixinTestCase, EventTestCase):
  moduleid = 'config'
  eventid  = 'config'
  _conf = """<config enabled="true">
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config>"""

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

class Test_ConfigRpmInputs(ConfigEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    ConfigEventTestCase.__init__(self, distro, version, arch, conf=conf)

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
        <trigger trigger="bash" type="triggerin">%(working-dir)s/script1</trigger>
        <trigger trigger="bash" type="triggerun">%(working-dir)s/script1</trigger>
        <trigger trigger="python" type="triggerpostun" interpreter="/bin/python">%(working-dir)s/script1</trigger>
        <trigger trigger="bash" type="triggerin" content="text">echo triggerin</trigger>
        <trigger trigger="bash" type="triggerun" content="text">echo triggerun</trigger>
        <trigger trigger="python" type="triggerpostun" interpreter="/bin/python" content="text">print triggerpostun</trigger>
      </config>
      """ % {'working-dir': self.working_dir})

  def setUp(self):
    ConfigEventTestCase.setUp(self)
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
    ConfigEventTestCase.tearDown(self)
    self.file1.rm(force=True)
    self.file2.rm(force=True)
    self.script1.rm(force=True)
    self.script2.rm(force=True)

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_inputs()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmBuild(ConfigEventTestCase):
  def setUp(self):
    ConfigEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars1(RpmCvarsTestCase, ConfigEventTestCase):
  def setUp(self):
    ConfigEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars2(RpmCvarsTestCase, ConfigEventTestCase):
  def setUp(self):
    ConfigEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_OutputsGpgkeys(ConfigEventTestCase):
  "creates output when gpgcheck enabled"
  def _make_repos_config(self):
    return ConfigEventTestCase._make_repos_config(self)

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

class Test_RemovesGpgkeys(ConfigEventTestCase):
  "removes output when gpgcheck disabled"
  # disable gpgcheck via /distribution/config/updates@gpgcheck
  _conf = """<config>
    <updates gpgcheck='false'/>
  </config>"""

  def _make_repos_config(self):
    return ConfigEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not (self.event.SOFTWARE_STORE/'gpgkeys').
                         findpaths())

class Test_ValidateDestnames(ConfigEventTestCase):
  "destname required for text content"  

  _conf = """<config>
    <files content="text">test</files>
  </config>"""

  def setUp(self): pass

  def runTest(self):
    self.tb = TestBuild(self.conf, self.options, [])
    # can't get unittest.TestCase.failUnlessRaises to work so, sigh, 
    # here's a copy of the code...
    try:
      self.tb.validate_configs()
    except InvalidConfigError:
      return
    else: 
      raise self.failureException, "InvalidConfigError not raised"

  def tearDown(self):
    self.tb._lock.release()
    del self.tb
    del self.conf

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('config')

  suite.addTest(make_core_suite(ConfigEventTestCase, distro, version, arch))
  suite.addTest(Test_ConfigRpmInputs(distro, version, arch))
  suite.addTest(Test_ConfigRpmBuild(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars1(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars2(distro, version, arch))
  suite.addTest(Test_OutputsGpgkeys(distro, version, arch))
  suite.addTest(Test_RemovesGpgkeys(distro, version, arch))
  suite.addTest(Test_ValidateDestnames(distro, version, arch))

  return suite
