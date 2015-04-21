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

from deploy.errors  import DeployError
from deploy.util    import pps
from deploy.util    import rxml

from dtest          import (BUILD_ROOT, TestBuild, EventTestCase, 
                            ModuleTestSuite, _run_make)
from dtest.core     import make_extension_suite
from dtest.mixins   import (MkrpmRpmBuildMixinTestCase, RpmCvarsTestCase,
                             DeployMixinTestCase,
                             dm_make_suite)


class ConfigRpmEventTestCase(MkrpmRpmBuildMixinTestCase, EventTestCase):
  """
  The config-rpms module reads user config and generates classes at runtime. In
  our test case we provide config that causes a class to be created, and then
  we test the functioning of that class.
  """
  moduleid = 'config-rpms'
  eventid  = 'config-rpm'
  _type = 'package'
  _conf = ["""<config-rpms>
  <config-rpm id='config'>
    <requires>yum</requires>
    <requires>createrepo</requires>
  </config-rpm>
  </config-rpms>"""]

class Test_ErrorOnDuplicateIds(ConfigRpmEventTestCase):
  "raises an error if multiple rpms provide the same id"
  _conf = """
  <config-rpms>
  <config-rpm id="config">test1</config-rpm>
  <config-rpm id="config">test2</config-rpm>
  </config-rpms>
  """

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, DeployError, 
      TestBuild, self.conf, options=self.options, args=[]) 

  def tearDown(self):
    del self.conf


class Test_ConfigRpmRepos(ConfigRpmEventTestCase):
  "repo added to repos cvar"
  _conf = """
  <config-rpms>
  <config-rpm id="config">
    <repo id='test'>
      <baseurl>file:///%s/repo1</baseurl>
    </repo>
  </config-rpm>
  </config-rpms>
  """ %  (pps.path(__file__).dirname/'shared')

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()

    # did config-rpm-setup-event add the rep?
    self.failUnless("test" in self.event.cvars['repos'])

    # did the repos event process it?
    self.failUnless(self.event.cvars['repos']['test'].localurl)


class ConfigRpmInputsEventTestCase(ConfigRpmEventTestCase):
  _conf = [""" 
  <config-rpms>
    <config-rpm id='config'>
    <!--setting name changes eventid, which we don't want for testing-->
    <!--<name>myrpm</name>-->
    <summary>myrpm summary</summary>
    <description>myrpm description</description>
    <license>MIT</license>
    <provides>myprovides</provides>
    <files destdir="/etc/testdir">%(working-dir)s/file1</files>
    <files destdir="/etc/testdir" destname="file4">
           %(working-dir)s/file2</files>
    <files destdir="/etc/testdir" destname="file5" content="text">text</files>
    <files destdir="/etc/testdir">%(working-dir)s/dir1</files>
    <script type="pre">echo pre</script>
    <script type="preun">echo preun</script>
    <script type="post">echo post</script>
    <script type="posttrans">echo posttrans</script>
    <script type="postun">echo postun</script>
    <trigger trigger="bash" type="triggerin">echo triggerin</trigger>
    <trigger trigger="bash" type="triggerun">echo triggerun</trigger>
    <trigger trigger="python" type="triggerpostun" 
             interpreter="/usr/bin/python">print triggerpostun</trigger>
    </config-rpm>
  </config-rpms>
  """ % { 'working-dir': BUILD_ROOT }]

  def __init__(self, os, version, arch, conf=None):
    ConfigRpmEventTestCase.__init__(self, os, version, arch, conf=conf)

    self.working_dir = BUILD_ROOT
    self.file1 = pps.path('%s/file1' % self.working_dir)
    self.file2 = pps.path('%s/file2' % self.working_dir)
    self.dir1  = pps.path('%s/dir1'  % self.working_dir)
    self.file3 = pps.path('%s/file3' % self.dir1)

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
    self.dir1.rm(force=True, recursive=True)

class Test_ConfigRpmInputs(ConfigRpmInputsEventTestCase):
  "test config-rpm inputs"
  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    self.check_inputs('files')

class Test_ConfigRpmBuild(ConfigRpmInputsEventTestCase):
  "test config-rpm build"
  def setUp(self):
    ConfigRpmInputsEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    self.check_header()

class Test_ConfigRpmCvars1(RpmCvarsTestCase, ConfigRpmEventTestCase):
  "test config-rpm cvars - first run"
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    self.check_cvars()

class Test_ConfigRpmCvars2(RpmCvarsTestCase, ConfigRpmEventTestCase):
  "test config-rpm cvars - subsequent runs"
  def setUp(self):
    ConfigRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    self.check_cvars()


class Test_ValidateDestnames(ConfigRpmEventTestCase):
  "destname required for text content"  
  _conf = """<config-rpms>
  <config-rpm id='config'>
    <files content="text">test</files>
  </config-rpm>
  </config-rpms>"""

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, DeployError, 
      TestBuild, self.conf, options=self.options, args=[]) 

  def tearDown(self):
    del self.conf

class DeployConfigRpmEventTestCase(DeployMixinTestCase, 
                                   ConfigRpmInputsEventTestCase):
  _type = 'system'
  _conf = ["""
  <publish>
  <script id='config-rpm' type='post'>
    #!/bin/bash
    set -e
    ls /etc/testdir/file1
    ls /etc/testdir/file4
    ls /etc/testdir/file5
    ls /etc/testdir/dir1/file3
  </script>
  </publish>
  """]
  _conf.extend(ConfigRpmInputsEventTestCase._conf)

  def __init__(self, os, version, arch, *args, **kwargs):
    ConfigRpmInputsEventTestCase.__init__(self, os, version, arch)
    DeployMixinTestCase.__init__(self, os, version, arch, module='publish')

  def setUp(self):
    ConfigRpmInputsEventTestCase.setUp(self)
    DeployMixinTestCase.setUp(self)

class Test_FilesInstalled(DeployConfigRpmEventTestCase):
  "files installed on client machine"

class Test_FilesPersistOnLibDirChanges(DeployConfigRpmEventTestCase):
  "files persist on clientdir changes"
  def runTest(self):
    self.event.test_client_dir = pps.path('/root/deploy')
    DeployMixinTestCase.runTest(self)    

class ConfigRpmVMShutdownEventTestCase(DeployMixinTestCase, 
                                       ConfigRpmEventTestCase):
  _type = 'system'

  def __init__(self, os, version, arch, *args, **kwargs):
    ConfigRpmEventTestCase.__init__(self, os, version, arch)
    DeployMixinTestCase.__init__(self, os, version, arch, module='publish')

def make_suite(os, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('config-rpms')

  suite.addTest(make_extension_suite(ConfigRpmEventTestCase, os, 
                                     version, arch))
  suite.addTest(Test_ErrorOnDuplicateIds(os, version, arch))
  suite.addTest(Test_ConfigRpmRepos(os, version, arch))
  suite.addTest(Test_ConfigRpmInputs(os, version, arch))
  suite.addTest(Test_ConfigRpmBuild(os, version, arch))
  suite.addTest(Test_ConfigRpmCvars1(os, version, arch))
  suite.addTest(Test_ConfigRpmCvars2(os, version, arch))
  suite.addTest(Test_ValidateDestnames(os, version, arch))

  suite.addTest(Test_FilesInstalled(os, version, arch))
  suite.addTest(Test_FilesPersistOnLibDirChanges(os, version, arch))
  suite.addTest(dm_make_suite(ConfigRpmVMShutdownEventTestCase, os, version, arch, ))

  return suite
