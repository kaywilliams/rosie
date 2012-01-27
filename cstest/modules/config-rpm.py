#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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

from centosstudio.util     import pps
from centosstudio.util     import repo
from centosstudio.util     import rxml
from centosstudio.validate import InvalidConfigError

from cstest          import (BUILD_ROOT, TestBuild, EventTestCase, 
                            ModuleTestSuite)
from cstest.core     import make_extension_suite
from cstest.mixins   import RpmBuildMixinTestCase, RpmCvarsTestCase


class ConfigRpmEventTestCase(RpmBuildMixinTestCase, EventTestCase):
  moduleid = 'config-rpm'
  eventid  = 'config-rpm'
  _conf = """<config-rpm enabled="true">
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config-rpm>"""

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    base = repo.getDefaultRepoById('base', distro=self.distro,
                                           version=self.version,
                                           arch=self.arch,
                                           include_baseurl=True,
                                           baseurl='http://www.centossolutions.org/mirrors/%s' % self.distro)
    base.update({'mirrorlist': None, 'gpgcheck': None})

    repos.append(base.toxml()) # don't overwrite gpgkey and gpgcheck defaults

    return repos

class Test_ConfigRpmInputs(ConfigRpmEventTestCase):
  def __init__(self, distro, version, arch, conf=None):
    ConfigRpmEventTestCase.__init__(self, distro, version, arch, conf=conf)

    self.working_dir = BUILD_ROOT
    self.file1 = pps.path('%s/file1' % self.working_dir)
    self.file2 = pps.path('%s/file2' % self.working_dir)
    self.dir1  = pps.path('%s/dir1'  % self.working_dir)
    self.file3 = pps.path('%s/file3' % self.dir1)

    self._add_config(
      """
      <config-rpm enabled="true">
        <files destdir="/etc/testdir">%(working-dir)s/file1</files>
        <files destdir="/etc/testdir" destname="file4">%(working-dir)s/file2</files>
        <files destdir="/etc/testdir" destname="file5" content="text">here is some text</files>
        <files destdir="/etc/testdir">%(working-dir)s/dir1</files>
        <!--<files destdir="/etc/testdir" destname="dir2" content="text">-->
        <script type="post">echo post</script>
        <script type="pre">echo pre</script>
        <script type="preun">echo preun</script>
        <script type="postun">echo postun</script>
        <script type="verifyscript">echo verifyscript</script>
        <trigger trigger="bash" type="triggerin">echo triggerin</trigger>
        <trigger trigger="bash" type="triggerun">echo triggerun</trigger>
        <trigger trigger="python" type="triggerpostun" interpreter="/bin/python">print triggerpostun</trigger>
      </config-rpm>
      """ % {'working-dir': self.working_dir})

  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.file1.touch()
    self.file2.touch()
    self.dir1.mkdir()
    self.file3.touch()
    self.clean_event_md()
    self.event.status = True

  def tearDown(self):
    if self.img_path:
      self.img_path.rm(recursive=True, force=True)
    ConfigRpmEventTestCase.tearDown(self)
    self.file1.rm(force=True)
    self.file2.rm(force=True)

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_inputs('files')
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmBuild(ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_header()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars1(RpmCvarsTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ConfigRpmCvars2(RpmCvarsTestCase, ConfigRpmEventTestCase):
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='config-rpm')
    self.check_cvars()
    self.failUnless(self.event.verifier.unittest().wasSuccessful())

class Test_ValidateDestnames(ConfigRpmEventTestCase):
  "destname required for text content"  
  _conf = """<config-rpm>
    <files content="text">test</files>
  </config-rpm>"""

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, InvalidConfigError, 
      TestBuild, self.conf, self.options, [])

  def tearDown(self):
    del self.conf


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('config-rpm')

  suite.addTest(make_extension_suite(ConfigRpmEventTestCase, distro, 
                                     version, arch))
  suite.addTest(Test_ConfigRpmInputs(distro, version, arch))
  suite.addTest(Test_ConfigRpmBuild(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars1(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars2(distro, version, arch))
  suite.addTest(Test_ValidateDestnames(distro, version, arch))

  return suite
