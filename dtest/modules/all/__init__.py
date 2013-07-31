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

from deploy.util import pps
from deploy.util.rxml import config, tree
from deploy.util.rxml.errors import MacroError

class AllEventTestCase(EventTestCase):
  """
  The all module is a container for all other events. For testing, we also 
  use/abuse it as a convenient mechanism for testing general Deploy 
  functionality.
  """
  moduleid = 'all'
  eventid  = 'all'
  _type = 'package'

# start the abuse...
class Test_XIncludeResolution(AllEventTestCase):
  "test xinclude resolution"

  _conf = ["""
  <config-rpms xmlns:xi='%s' xml:base='%s'>

  <config-rpm id='test'>

  <!--case 1: local xpointer to elem-->
  <xi:include xpointer="xpointer(//config-rpm[@id='target']/files)"/>

  <!--case 2: local xpointer to text-->
  <files destdir='/case2'>
  <xi:include xpointer="xpointer(//config-rpm[@id='target']/files/text())"/>
  </files>

  <!--case 3: include remote text file-->
  <files content='text' destdir='/case3' destname='file.txt'>
  <xi:include href="file.txt" parse="text"/>
  </files>

  <!--case 4: tail after include elem-->
  <files content='text' destdir='/case4' destname='file.txt'>
  <xi:include href="file.txt" parse="text"/>
  tail text
  </files>

  <!--case 5: macro in include attributes-->
  <macro id='5'>5</macro>
  <files content='text' destdir='/case%%{5}' destname='file.txt'>text</files>
  </config-rpm>

  <!--case 6: nested includes-->
  <config-rpm id='case6'>
  <xi:include xpointer="xpointer(//config-rpm[@id='case6a']/*)"/>
  </config-rpm>
  <config-rpm id='case6a'>
  <files content='text' destdir='/case6' destname='file.txt'>
  <xi:include xpointer="xpointer(//config-rpm[@id='case6b']/files/text())"/>i
  </files>
  </config-rpm>
  <config-rpm id='case6b'>
  <files destdir='/test' destname='test'>case 6</files>
  </config-rpm>
  
  <!--local xinclude target-->
  <config-rpm id='target'>
  <files destdir='/case1'>test</files>
  </config-rpm>

  </config-rpms>
  """ % (tree.XI_NS, pps.path(__file__).abspath()),
  """
  <publish xmlns:xi='%s' xml:base='%s'>
  <!--case 7: remote xml file with xpointer-->
  <xi:include href='%%{templates-dir}/libvirt/deploy.xml'
              xpointer='xpointer(/*/*)'/>
  </publish>
  """ % (tree.XI_NS, pps.path(__file__).abspath()),]
  

  def runTest(self):
    xp = '/*/config-rpms/config-rpm/files'
    # case 1
    (self.failUnless(self.conf.getxpath('%s[@destdir="/case1"]' % xp) 
                    is not None))

    # case 2
    (self.failUnless(self.conf.getxpath('%s[@destdir="/case2"]/text()' % xp)
                     == 'test'))

    # case 3
    self.failUnless('some text' in self.conf.getxpath(
                    '%s[@destdir="/case3"]/text()' % xp))
    
    # case 4
    result = self.conf.getxpath('%s[@destdir="/case4"]/text()' % xp)
    self.failUnless('some text' in result and 'tail text' in result)

    # case 5
    (self.failUnless(self.conf.getxpath('%s[@destdir="/case5"]' % xp)
                     is not None))

    # case 6
    self.failUnless('case 6' in self.conf.getxpath(
                    '%s[@destdir="/case6"]/text()' % xp))

    # case 7 
    self.failUnless(self.conf.getxpath('/*/publish/kickstart') is not None)
    

class Test_MacroResolution(AllEventTestCase):
  "test macro resolution"

  def __init__(self, os, version, arch):
    EventTestCase.__init__(self, os, version, arch)
    name = 'test-%s' % self.moduleid
    xml = """
<definition>
<macro id='repoid'>repoid</macro>
<macro id='group-name'>group</macro>

<main>
<fullname>%(moduleid)s event test</fullname>
<name>%(name)s</name>
<os>%(os)s</os>
<arch>%(arch)s</arch>
<version>%(version)s</version>
<id>%(name)s-%(os)s-%(version)s-%(arch)s</id>
</main>

<repos>
<repo id='test'>
<baseurl>test</baseurl>
</repo>
</repos>

<packages>
  <!-- case 1 - macro with whitespace -->
  <macro id='space'> </macro>
  <group repoid='case1'>some%%{space}space</group>

  <!-- case 2 - macro in attribute -->
  <macro id='case2'>case2</macro>
  <group repoid='%%{case2}'>case2</group>
  
  <!-- case 3 - string macro in text -->
  <macro id='case3'>case3</macro>
  <package>%%{case3}</package>

  <!-- case 4 - string macro in tail -->
  <macro id='case4'>case4</macro>
  <package><!-- macro follows a comment element-->%%{case4}</package>
</packages>

<config-rpms>
  <!-- case 5 - element macro in text/text -->
  <macro id='case5a'><files>case5a.txt</files></macro><!--w/ following text-->
  <macro id='case5b'><files>case5b.txt</files></macro><!--w/ leading text-->
  <macro id='case5c'><files>case5c.txt</files></macro><!--in element tail-->
  <macro id='case5d'><!-- elem with multiple sub elements-->
    <files>case5d1.txt</files>
    <files>case5d2.txt</files>
    <files>case5d3.txt</files>
  </macro>
  <config-rpm id='case5'>
  %%{case5a}
  %%{case5b}
  <files>some.txt</files>
  %%{case5c}
  %%{case5d}
  </config-rpm>
</config-rpms>

<!-- case 6 macro with text, elems and tail -->
<macro id ='case6'>
case6 
<elem/>
<elem/>
</macro>

<publish>
<kickstart>
text %%{case6} tail 
text before macro
<macro id='text'/> <!--macro in text-->
text following macro
</kickstart>
text %%{case6} tail

<!-- case 7 - nested macro placeholders -->
<macro id="case7">case7</macro>
<macro id="case7-text"><script id='case7a'/></macro>
<macro id="text-case7"><script id='case7b'/></macro>
<macro id="text-case7-text"><script id='case7c'/></macro>
%%{%%{case7}-text}
%%{text-%%{case7}}
%%{text-%%{case7}-text}
</publish>
</definition>
    """ % {'moduleid': self.moduleid,
           'name':     name,
           'os':       os,
           'version':  version,
           'arch':     arch}

    self.conf = config.parse(StringIO(xml), xinclude=True, remove_macros=True
                            ).getroot()

  def setUp(self): pass

  def runTest(self):
    expected_results = [ """
    <packages>
      <group repoid='case1'>some space</group>
      <group repoid="case2">case2</group>
      <package>case3</package>
      <package>case4</package>
    </packages>
    """,
    """
    <config-rpms>
      <config-rpm id="case5">
        <files>case5a.txt</files>
        <files>case5b.txt</files>
        <files>some.txt</files>
        <files>case5c.txt</files>
        <files>case5d1.txt</files>
        <files>case5d2.txt</files>
        <files>case5d3.txt</files>
      </config-rpm>
    </config-rpms>
    """,
    """<publish>
  <kickstart>text 
case6
    <elem/>
    <elem></elem>
 tail 
text before macro
 
text following macro

  </kickstart>
text 
case6 

  <elem/>
  <elem></elem>
 tail
 <script id='case7a'/>
 <script id='case7b'/>
 <script id='case7c'/>
</publish>
""" ]

    for section in expected_results:
      expected = config.parse(StringIO(section)).getroot()
      # print "expected:", expected
      # print "existing:", self.conf.getxpath('/*/%s' % expected.tag)
      self.failUnless(expected == self.conf.getxpath('/*/%s' % expected.tag))

  def tearDown(self): pass

class Test_MacroFailsOnCircularReference(AllEventTestCase):
  "macro fails on circular reference "

  _conf = """
  <macro id='test'>%{test}</macro>
  """
  def setUp(self): pass 

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, MacroError,
      TestBuild, self.conf, self.options, [])

  def tearDown(self): pass

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('all')

  suite.addTest(make_core_suite(AllEventTestCase, os, version, arch))
  suite.addTest(Test_XIncludeResolution(os, version, arch))
  suite.addTest(Test_MacroResolution(os, version, arch))
  suite.addTest(Test_MacroFailsOnCircularReference(os, version, arch))

  return suite
