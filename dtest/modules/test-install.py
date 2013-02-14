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

from deploy.errors import DeployError
from deploy.util   import pps 
from deploy.util   import rxml 

from deploy.util.rxml import datfile

from dtest      import EventTestCase, ModuleTestSuite, TestBuild
from dtest.core import make_extension_suite

from dtest.mixins import (psm_make_suite, DeployMixinTestCase,
                           dm_make_suite, check_vm_config)


class PublishSetupEventTestCase(DeployMixinTestCase, EventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install-setup'

  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(
        self.event.cvars['%s-setup-options' % self.moduleid]['localpath'])
    EventTestCase.tearDown(self)


class TestInstallEventTestCase(PublishSetupEventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install'
  _conf = ["""
  <test-install>
    <script id='test' type='post'>
    <!--comment-->
    echo "test to ensure comments work inside script elements"
    echo "ps. this is dumb, we should really fix comments during parsing"
    </script>
  </test-install>
  """]

  def __init__(self, os, version, arch, *args, **kwargs):
    PublishSetupEventTestCase.__init__(self, os, version, arch, *args, **kwargs)

  def setUp(self):
    PublishSetupEventTestCase.setUp(self)

    if not self.event: # module disabled
      return

    # set password and crypt password in datfile
    root = self.event.parse_datfile()
    mod = root.getxpath('%s' % self.moduleid, '')
    if len(mod) == 0:
      mod = datfile.uElement('%s' % self.moduleid, parent=root)
    datfile.uElement('crypt-password', text='$6$OJZ6KCfu$GcpaU07JTXN1y/bMSunZJDt.BBMOl1gs7ZoJy1c6No4iJyyXUFhD3X2ar1ZT2qKN/NS9KLDoyczmuIfVyDPiZ/', parent=mod)
    root.write()

  def tearDown(self):
    EventTestCase.tearDown(self) 

class Test_ErrorOnDuplicateIds(TestInstallEventTestCase):
  "raises an error if multiple scripts provide the same id"

  def setUp(self): pass

  def runTest(self):
    parent = self.conf.getxpath('test-install')
    script = rxml.config.Element('script', parent=parent, 
                                 attrs={'id':   'test',
                                        'type': 'post-script'})
    script.text = 'echo "hello"'
    script = rxml.config.Element('script', parent=parent, 
                                 attrs={'id':   'test',
                                        'type': 'post-script'})
    script.text = 'echo "hello"'
    unittest.TestCase.failUnlessRaises(self, DeployError,
      TestBuild, self.conf, self.options, [])

  def tearDown(self):
    del self.conf

class Test_ErrorOnSshDisabled(TestInstallEventTestCase):
  "raises an error if SSH disabled and required by scripts"

  def setUp(self):
    parent = self.conf.getxpath('test-install')
    rxml.config.Element('ssh', parent=parent, text='false')
    EventTestCase.setUp(self) 

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)

class Test_ComesBeforeComesAfter(TestInstallEventTestCase):
  "test comes-before and comes-after"

  def runTest(self):
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, text='echo test', 
                                 attrs={'id':   'id3',
                                        'type': 'post',})
    script = rxml.config.Element('script', parent=parent, text='echo test',
                                 attrs={'id':   'id4',
                                        'type': 'post',})
    script = rxml.config.Element('script', parent=parent, text='echo test',
                                 attrs={'id':   'test-comes',
                                        'type': 'post',
                                        'comes-after': 'id1, id2 id3',
                                        'comes-before': 'id4 id5',
                                        })
    self.execute_predecessors(self.event)
    self.event.setup()
    self.failUnless(self.event.scripts['test-comes'].conditionally_comes_after
                    == set(['id1', 'id2', 'id3']))
    self.failUnless(self.event.scripts['test-comes'].conditionally_comes_before
                    == set(['id4', 'id5']))
    ids = [ x.id for x in self.event.types['post'] ]
    test_comes_id = ids.index('test-comes')
    self.failUnless('id3' in ids[:test_comes_id] and 
                    'id4' in ids[test_comes_id+1:])

class ReinstallTestInstallEventTestCase(TestInstallEventTestCase):
  def setUp(self):
    TestInstallEventTestCase.setUp(self)

    # tell event to raise an error rather than reinstall if install
    # triggers fail
    self.event.test_fail_on_reinstall = True


class Test_ReinstallOnReleaseRpmChange(ReinstallTestInstallEventTestCase):
  "reinstalls if release-rpm changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    name = self.event.cvars['release-rpm']
    self.event.cvars['rpmbuild-data'][name]['rpm-release'] += '1'
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnConfigRpmChange(ReinstallTestInstallEventTestCase):
  "reinstalls if config-rpm changes"
  _conf = ["""
  <config-rpms>
  <config-rpm id='test-config'>
  <script type='post'>echo 'hello'</script>
  </config-rpm>
  </config-rpms>
  """]

  def __init__(self, os, version, arch, *args, **kwargs):
    ReinstallTestInstallEventTestCase.__init__(self, os, version, arch, *args, **kwargs)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnKickstartChange(ReinstallTestInstallEventTestCase):
  "reinstalls if kickstart changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.cvars['test-install-kstext'] = ''
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnTreeinfoChange(ReinstallTestInstallEventTestCase):
  "reinstalls if treeinfo changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.cvars['base-treeinfo-text'] = ''
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnInstallScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if an install script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, 
                                 attrs={'id':   'install-test',
                                        'type': 'install'})
    script.text = 'echo "Hello"'
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnPostInstallScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if a post-install script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, 
                                 attrs={'id':   'post-install-test',
                                        'type': 'post-install'})
    script.text = 'echo "hello"'
    self.failUnlessRaises(DeployError, self.event)

class Test_ReinstallOnSaveTriggersScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if a save-triggers script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, 
                                 attrs={'id':   'save-triggers-test',
                                        'type': 'save-triggers'})
    script.text = 'echo "hello"'
    self.failUnlessRaises(DeployError, self.event)

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-install')

  # setup
  suite.addTest(make_extension_suite(PublishSetupEventTestCase, os, version, arch))
  suite.addTest(psm_make_suite(PublishSetupEventTestCase, os, version, arch))

  # deploy
  if check_vm_config():
    suite.addTest(make_extension_suite(TestInstallEventTestCase, os, version, arch))
    suite.addTest(Test_ErrorOnDuplicateIds(os, version, arch))
    suite.addTest(Test_ErrorOnSshDisabled(os, version, arch))
    suite.addTest(Test_ComesBeforeComesAfter(os, version, arch))
    suite.addTest(Test_ReinstallOnReleaseRpmChange(os, version, arch))
    suite.addTest(Test_ReinstallOnConfigRpmChange(os, version, arch))
    suite.addTest(Test_ReinstallOnKickstartChange(os, version, arch))
    suite.addTest(Test_ReinstallOnTreeinfoChange(os, version, arch))
    suite.addTest(Test_ReinstallOnInstallScriptChange(os, version, arch))
    suite.addTest(Test_ReinstallOnPostInstallScriptChange(os, version, arch))
    suite.addTest(Test_ReinstallOnSaveTriggersScriptChange(os, version, arch))
    # dummy test to shutoff vm
    suite.addTest(dm_make_suite(TestInstallEventTestCase, os, version, arch, ))

  return suite
