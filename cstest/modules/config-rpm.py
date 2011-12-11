#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
from centosstudio.util     import pps
from centosstudio.util     import repo
from centosstudio.util     import rxml
from centosstudio.validate import InvalidConfigError
from centosstudio.util.pps.constants import TYPE_NOT_DIR

from cstest          import (BUILD_ROOT, TestBuild, EventTestCase, 
                            ModuleTestSuite, PUBKEY, SECKEY)
from cstest.core     import make_core_suite
from cstest.rpmbuild import RpmBuildMixinTestCase, RpmCvarsTestCase

class ConfigRpmEventTestCase(RpmBuildMixinTestCase, EventTestCase):
  moduleid = 'config-rpm'
  eventid  = 'config-rpm'
  _conf = """<config-rpm enabled="true">
    <gpgsign>
      <public>%s</public>
      <secret>%s</secret>
    </gpgsign>
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config-rpm>""" % (PUBKEY, SECKEY)

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    base = repo.getDefaultRepoById('base', distro=self.distro,
                                           version=self.version,
                                           arch=self.arch,
                                           include_baseurl=True,
                                           baseurl='http://www.renditionsoftware.com/mirrors/%s' % self.distro)
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
        <gpgsign>
          <public>%(pubkey)s</public>
          <secret>%(seckey)s</secret>
        </gpgsign>
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
      """ % {'working-dir': self.working_dir, 
             'pubkey': PUBKEY, 
             'seckey': SECKEY})

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
    self.check_inputs()
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

class Test_OutputsGpgkeys(ConfigRpmEventTestCase):
  "creates output when gpgcheck enabled"
  def _make_repos_config(self):
    return ConfigRpmEventTestCase._make_repos_config(self)

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

class Test_RemovesGpgkeys(ConfigRpmEventTestCase):
  "removes output when gpgcheck disabled"
  _conf = """<config-rpm>
    <gpgsign>
      <public>%s</public>
      <secret>%s</secret>
    </gpgsign>
    <updates gpgcheck='false'/>
  </config-rpm>""" % (PUBKEY, SECKEY)

  def _make_repos_config(self):
    return ConfigRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not (self.event.SOFTWARE_STORE/'gpgkeys').
                         findpaths())

class Test_ValidateDestnames(ConfigRpmEventTestCase):
  "destname required for text content"  

  _conf = """<config-rpm>
    <gpgsign>
      <public>%s</public>
      <secret>%s</secret>
    </gpgsign>
    <files content="text">test</files>
  </config-rpm>""" % (PUBKEY, SECKEY)

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

class Test_GeneratesSigningKeys(ConfigRpmEventTestCase):
  "Generates signing keys"
  _conf = """<config-rpm/>"""

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    xpath = '/*/rpms/%s' % self.event.id
    self.failUnless(self.datfile.get('%s/pubkey' % xpath, None) is not None and
                    self.datfile.get('%s/seckey' % xpath, None) is not None) 

def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('config-rpm')

  suite.addTest(make_core_suite(ConfigRpmEventTestCase, distro, version, arch))
  suite.addTest(Test_ConfigRpmInputs(distro, version, arch))
  suite.addTest(Test_ConfigRpmBuild(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars1(distro, version, arch))
  suite.addTest(Test_ConfigRpmCvars2(distro, version, arch))
  suite.addTest(Test_OutputsGpgkeys(distro, version, arch))
  suite.addTest(Test_RemovesGpgkeys(distro, version, arch))
  suite.addTest(Test_ValidateDestnames(distro, version, arch))
  if not kwargs['skip_genkey_tests']:
    suite.addTest(Test_GeneratesSigningKeys(distro, version, arch))

  return suite
