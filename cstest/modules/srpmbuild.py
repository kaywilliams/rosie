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

from centosstudio.modules.core.rpmbuild.gpgsign import InvalidKeyError

from cstest        import (EventTestCase, ModuleTestSuite, _run_make,
                           TestBuild)
from cstest.core   import make_core_suite
from cstest.mixins import check_vm_config

REPODIR  = pps.path(__file__).dirname/'shared' 

class TestSrpmTestCase(EventTestCase):
  """
  The srpmbuild module reads user config and generates classes at runtime. In
  our test case we provide config that causes a class to be generated, and then
  we test the functioning of that class
  """
  moduleid = 'srpmbuild'
  eventid  = 'package1-srpm'
  _type = 'package'

  _run_make(REPODIR)
  _conf = ["""
    <srpmbuild>
    <srpm id='package1' shutdown='false'>
      <path>%s/repo1/SRPMS/package1-1.0-1.src.rpm</path>
    </srpm>
    </srpmbuild>
    """ % REPODIR] 

  def __init__(self, distro, version, arch, conf=None):
    EventTestCase.__init__(self, distro, version, arch, conf=conf)

class Test_ErrorOnDuplicateIds(TestSrpmTestCase):
  "raises an error if multiple rpms provide the same id"
  _conf = """
  <srpmbuild>
  <srpm id="test"/>
  <srpm id="test"/>
  </srpmbuild>
  """

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, CentOSStudioError,
      TestBuild, self.conf, self.options, [])

  def tearDown(self):
    del self.conf


class Test_Config(TestSrpmTestCase):
  "fails if path, repo or script elements not provided"
  _conf = """
    <srpmbuild>
    <srpm id='package1' shutdown='false'/>
    </srpmbuild>
    """ 

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, CentOSStudioError, 
      TestBuild, self.conf, self.options, [])

  def tearDown(self):
    del self.conf


class Test_FromFolder(TestSrpmTestCase):
  "downloads srpm file from folder"
  _conf = """
    <srpmbuild>
    <srpm id='package1' shutdown='false'>
      <path>%s/repo1/SRPMS</path>
    </srpm>
    </srpmbuild>
    """ % REPODIR 

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')


class Test_FromRepo(TestSrpmTestCase):
  "downloads srpm file from repository"
  _conf = """
    <srpmbuild>
    <srpm id='package1' shutdown='false'>
      <repo>file://%s/repo1</repo>
    </srpm>
    </srpmbuild>
    """ % REPODIR 

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.failUnless(self.event.io.list_output(what='srpm')[0].basename  == 
                   'package1-1.0-2.src.rpm')


class Test_FromScript(TestSrpmTestCase):
  "uses srpm provided by script"
  _conf = """
      <srpmbuild>
      <srpm id='package1' shutdown='false'>
        <script>
        #!/bin/bash
        srpm=%s/repo1/SRPMS/package1-1.0-2.src.rpm
        if [[ $srpm != '%%{srpm-last}' ]]; then 
          cp -a $srpm '%%{srpm-dir}'
        fi
        </script>
      </srpm>
      </srpmbuild>
      """ % REPODIR

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')

class Test_UpdatesDefinition(TestSrpmTestCase):
  "updates build machine definition"
  public = '-----BEGIN PGP PUBLIC - test'
  secret = '-----BEGIN PGP PRIVATE - test'

  _conf = [
  """
  <gpgsign>
    <public>%s</public>
    <secret>%s</secret>
  </gpgsign>
  """ % (public, secret)]
  _conf.extend(TestSrpmTestCase._conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    definition = self.event._update_definition()

    #set some convenience variables
    public = definition.get('/*/gpgsign/public/text()', '')
    secret = definition.get('/*/gpgsign/secret/text()', '')
    parent_repo = self.conf.get('/*/repos/repo[@id="base"]')
    child_repo = definition.get('/*/repos/repo[@id="base"]')

    self.failUnless(len(public) == len(self.public) and
                    len(secret) == len(self.secret) and
                    child_repo == parent_repo)

class Test_InvalidRpm(TestSrpmTestCase):
  "fails on invalid rpms"

  def runTest(self):
    self.event.test_verify_rpms = True
    self.execute_predecessors(self.event)
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_Apply(TestSrpmTestCase):
  "rpmbuild-data added for generated rpm(s)"

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless('package1' in self.event.cvars['rpmbuild-data'])


class Test_Shutdown(TestSrpmTestCase):
  "dummy case to shutdown virtual machine"

  def runTest(self):
    self.event.config.get('.').set('shutdown', 'true')
    self.tb.dispatch.execute(until=self.event)


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('srpmbuild')

  if check_vm_config():
    suite.addTest(make_core_suite(TestSrpmTestCase, distro, version, arch))
    suite.addTest(Test_ErrorOnDuplicateIds(distro, version, arch))
    suite.addTest(Test_Config(distro, version, arch))
    suite.addTest(Test_FromFolder(distro, version, arch))
    suite.addTest(Test_FromRepo(distro, version, arch))
    suite.addTest(Test_FromScript(distro, version, arch))
    suite.addTest(Test_UpdatesDefinition(distro, version, arch))
    suite.addTest(Test_InvalidRpm(distro, version, arch))
    suite.addTest(Test_Apply(distro, version, arch))
    suite.addTest(Test_Shutdown(distro, version, arch))
    return suite
