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

from StringIO import StringIO

from dtest      import EventTestCase, ModuleTestSuite, TestBuild
from dtest.core import make_core_suite

from deploy.errors import DeployError
from deploy.util.rxml import config
from deploy.util.rxml.errors import XIncludeSyntaxError

class AllEventTestCase(EventTestCase):
  """
  The all module is a container for all other events. For testing, we also 
  use/abuse it as a convenient mechanism for testing general Deploy 
  functionality.
  """
  moduleid = 'all'
  eventid  = 'all'
  _mode = 'package'

# start the abuse...
class Test_MacroResolution(AllEventTestCase):
  "test macro resolution"

  _global_macros = """
  <macro id='repoid'>repoid</macro>
  <macro id='group-name'>group</macro>
  <macro id='pkg-elem'><package>package</package></macro>
  <macro id='config-elem'><config-rpm id='config'/></macro>
  <macro id='srpm1-elem'><srpm id='srpm1'><path>/</path></srpm></macro>
  <macro id='srpm2-elem'><srpm id='srpm2'><path>/</path></srpm></macro>
  """ 

  _conf = [ """
  <packages>
    %{pkg-elem}<!--elem in text-->
    <group repoid='%{repoid}'>%{group-name}</group><!--attrib and string-->
    %{%{extra}-packages} <!--nested macro references-->
    <macro id='extra'>extra</macro> <!--module-level macro-->
    <macro id='extra-packages'> <!--macro def with macro content-->
      <package>extra-package-1</package>
      <package>%{extra-package-2}</package>
      %{extra-package-empty} 
      %{extra-package-null} 
    </macro>
    <macro id='extra-package-2'>extra-package-2</macro>
    <macro id="extra-package-empty"></macro> <!--empty macro-->
    <macro id="extra-package-null"/> <!--null macro-->
  </packages>
  """,
  """
  <config-rpms>
    <config-rpm id='test'/>
    %{config-elem}<!--elem in tail-->
  </config-rpms>
  """,
  """
  <srpmbuild>
    %{srpm1-elem}<!--elem in both text and tail-->
    <srpm id='test'><path>/</path></srpm>
    %{srpm2-elem}<!--elem in both text and tail-->
  </srpmbuild>
  """,
  """
  <publish>
    <kickstart>
    text before macro
    <macro id='text'/>
    text following macro
    </kickstart>
  </publish>
  """]

  def runTest(self):
    expected_results = [ """
    <packages>
      <package>package</package>
      <group repoid="repoid">group</group>
      <package>extra-package-1</package>
      <package>extra-package-2</package>
    </packages>
    """,
    """
    <config-rpms>
      <config-rpm id="test"/>
      <config-rpm id="config"/>
    </config-rpms>
    """,
    """
    <srpmbuild>
      <srpm id="srpm1">
        <path>/</path>
      </srpm>
      <srpm id="test">
        <path>/</path>
      </srpm>
      <srpm id="srpm2">
        <path>/</path>
      </srpm>
    </srpmbuild>
    """,
    """
    <publish>
      <kickstart>
      text before macro
      text following macro
      </kickstart>
    </publish>
    """ ]

    for section in expected_results:
      expected = config.parse(StringIO(section), resolve_macros=False).getroot()
      # print "expected:", expected
      # print "existing:", self.conf.getxpath('/*/%s' % expected.tag)
      self.failUnless(expected == self.conf.getxpath('/*/%s' % expected.tag))

class Test_MacroFailsInXincludes(AllEventTestCase):
  "macros fail in XIncludes"

  _conf = """
  <macro id='test'>
  <include xmlns='http://www.w3.org/2001/XInclude' href='%{some_macro}'/>
  </macro>
  """
  def __init__(self, os, version, arch):
    unittest.TestCase.__init__(self)
    unittest.TestCase.failUnlessRaises(self, XIncludeSyntaxError,
      EventTestCase.__init__, self, os, version, arch)

  def setUp(self): pass
  def runTest(self): pass
  def tearDown(self): pass

class Test_MacroFailsOnCircularReference(AllEventTestCase):
  "macro fails on circular reference "

  _global_macros = """
  <macro id='test'>%{test}</macro>
  """
  def setUp(self): pass 

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, DeployError,
      TestBuild, self.conf, self.options, [])

  def tearDown(self): pass

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('all')

  suite.addTest(make_core_suite(AllEventTestCase, os, version, arch))
  suite.addTest(Test_MacroResolution(os, version, arch))
  suite.addTest(Test_MacroFailsInXincludes(os, version, arch))
  suite.addTest(Test_MacroFailsOnCircularReference(os, version, arch))

  return suite
