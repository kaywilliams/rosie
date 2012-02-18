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

from cstest       import (EventTestCase, ModuleTestSuite, _run_make,
                          TestBuild)
from cstest.core  import make_core_suite


class TestSrpmTestCase(EventTestCase):
  """
  The srpmbuild module reads user config and generates classes at runtime. In
  our test case we provide config that causes a class to be generated, and then
  we test the functioning of that class
  """
  moduleid = 'srpmbuild'
  eventid  = 'package1-srpm'
  repodir  = pps.path(__file__).dirname/'shared' 

  _run_make(repodir)

  def __init__(self, distro, version, arch, conf=None):
    EventTestCase.__init__(self, distro, version, arch, conf=conf)
    sections = [
      """
      <build-machine>
      <definition>
        %s/../../share/centosstudio/examples/rpmbuild/rpmbuild-%s-%s.definition
      </definition>
      </build-machine>
      """ % (pps.path(__file__).dirname.abspath(), version, arch),
      """
      <srpmbuild>
      <srpm id='package1'>
        <path>%s/repo1/SRPMS/package1-1.0-1.src.rpm</path>
      </srpm>
      </srpmbuild>
      """ % self.repodir ,
      ]
    for section in sections:
      self._add_config(section)

  def setUp(self):
    EventTestCase.setUp(self)

class TestSrpmBuildConfig(TestSrpmTestCase):
  "path, repo, or script element required"
  def __init__(self, distro, version, arch, conf=None):
    TestSrpmTestCase.__init__(self, distro, version, arch, conf=conf)
    self._add_config( """
      <srpmbuild>
      <srpm id='package1'/>
      </srpmbuild>
      """) 

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, CentOSStudioError, 
      TestBuild, self.conf, self.options, [])

  def tearDown(self):
    del self.conf

class TestSrpmBuildSrpmFolder(TestSrpmTestCase):
  "downloads srpm file from folder"
  def __init__(self, distro, version, arch, conf=None):
    TestSrpmTestCase.__init__(self, distro, version, arch, conf=conf)
    self._add_config( """
      <srpmbuild>
      <srpm id='package1'>
        <path>%s/repo1/SRPMS</path>
      </srpm>
      </srpmbuild>
      """ % self.repodir )

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')

class TestSrpmBuildSrpmRepo(TestSrpmTestCase):
  "downloads srpm file from repository"
  def __init__(self, distro, version, arch, conf=None):
    TestSrpmTestCase.__init__(self, distro, version, arch, conf=conf)
    self._add_config( """
      <srpmbuild>
      <srpm id='package1'>
        <repo>file://%s/repo1</repo>
      </srpm>
      </srpmbuild>
      """ % self.repodir )

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')

class TestSrpmBuildSrpmScript(TestSrpmTestCase):
  "uses srpm provided by script"
  def __init__(self, distro, version, arch, conf=None):
    TestSrpmTestCase.__init__(self, distro, version, arch, conf=conf)
    self._add_config( """
      <srpmbuild>
      <srpm id='package1'>
        <script>
        #!/bin/bash
        srpm=%s/repo1/SRPMS/package1-1.0-2.src.rpm
        if [[ $srpm != '%%{srpm-last}' ]]; then 
          cp -a $srpm '%%{srpm-dir}'
        fi
        </script>
      </srpm>
      </srpmbuild>
      """ % self.repodir )

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')
    
def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('srpmbuild')

  # srpm test cases require libvirt
  try: 
    import libvirt
  except ImportError:
    print "unable to import libvirt, skipping srpmbuild tests"

  suite.addTest(make_core_suite(TestSrpmTestCase, distro, version, arch))
  suite.addTest(TestSrpmBuildConfig(distro, version, arch))
  suite.addTest(TestSrpmBuildSrpmFolder(distro, version, arch))
  suite.addTest(TestSrpmBuildSrpmRepo(distro, version, arch))
  suite.addTest(TestSrpmBuildSrpmScript(distro, version, arch))
  return suite
