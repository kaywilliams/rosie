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

from deploy.util.rxml import config 

from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_extension_suite

from dtest.mixins import (psm_make_suite, PublishSetupMixinTestCase, 
                          DeployMixinTestCase, dm_make_suite)
from dtest.mixins import PackagesMixinTestCase, packages_mixin_make_suite


class TestInstallPackagesEventTestCase(PackagesMixinTestCase, EventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install-packages'


class TestInstallSetupEventTestCase(PublishSetupMixinTestCase, EventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install-setup'


class TestInstallEventTestCase(EventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install'


class Test_CommentsInScripts(TestInstallEventTestCase):
  "test comments in script elements"
  _conf = [
"""
<packages><package>kernel</package></packages>
""",
"""
<test-install>
  <script id='test' type='post'>
  <!--comment-->
  echo "test to ensure comments work inside script elements"
  </script>
</test-install>
"""
]

class Test_HostnameFile(TestInstallEventTestCase):
  "reads and validates user-provided ssh-host-file"
  hostname="bad_hostname"
  _conf = [
"""
<packages><package>kernel</package></packages>
""",
"""
<test-install>
<script id='write-hostfile' type='install'>
echo "%s" > %%{ssh-host-file}
</script>

<script id='read-hostfile' type='post'>
# dummy script to initiate hostfile reading
</script>
</test-install>
""" % hostname
]
  
  def runTest(self):
    try:
      self.tb.dispatch.execute(until=self.eventid)
    except DeployError as e:
      self.event.ssh_host_file.rm(force=True)
      self.failUnless("invalid" in str(e).lower() and self.hostname in str(e))
    else:
      self.event.ssh_host_file.rm(force=True)
      self.fail("DeployError not raised")


class Test_SshHost(TestInstallEventTestCase):
  "resolves ssh-host macro"
  _conf = ["""
<packages><package>kernel</package></packages>
""",
"""
<test-install>
<script id='test' type='pre'>
echo %{ssh-host}
</script>
</test-install>
"""]
  
  def runTest(self):
    self.tb.dispatch.execute(until=self.eventid)
    self.failIf("%{ssh-host}" in 
                self.event.io.list_output(what='test')[0].read_text())

class TestInstallDeployEventTestCase(DeployMixinTestCase,
                                     TestInstallEventTestCase):
   pass                                  

class Test_ErrorOnDuplicateIds(TestInstallDeployEventTestCase):
  "raises an error if multiple scripts provide the same id"

  def runTest(self):
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, text='echo test1', 
                                 attrib={'id':   'test',
                                        'type': 'post'})
    script = rxml.config.Element('script', parent=parent, text='echo test2',
                                 attrib={'id':   'test',
                                        'type': 'post'})
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)



class Test_ComesBeforeComesAfter(TestInstallDeployEventTestCase):
  "comes-before and comes-after resolve correctly"

  def runTest(self):
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, text='echo test', 
                                 attrib={'id':   'id3',
                                        'type': 'post',})
    script = rxml.config.Element('script', parent=parent, text='echo test',
                                 attrib={'id':   'id4',
                                        'type': 'post',})
    script = rxml.config.Element('script', parent=parent, text='echo test',
                                 attrib={'id':   'test-comes',
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

class ReinstallTestInstallEventTestCase(TestInstallDeployEventTestCase):
  def setUp(self):
    EventTestCase.setUp(self)
    DeployMixinTestCase.setUp(self)

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

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnKickstartChange(ReinstallTestInstallEventTestCase):
  "reinstalls if kickstart changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.cvars['test-install-ksfile'] = None
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
                                 attrib={'id':   'install-test',
                                        'type': 'install'})
    script.text = 'echo "Hello"'
    self.failUnlessRaises(DeployError, self.event)


class Test_ReinstallOnPostInstallScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if a post-install script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, 
                                 attrib={'id':   'post-install-test',
                                        'type': 'post-install'})
    script.text = 'echo "hello"'
    self.failUnlessRaises(DeployError, self.event)

class Test_ReinstallOnSaveTriggersScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if a save-triggers script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    parent = self.event.config.getxpath('.')
    script = rxml.config.Element('script', parent=parent, 
                                 attrib={'id':   'save-triggers-test',
                                        'type': 'save-triggers'})
    script.text = 'echo "hello"'
    self.failUnlessRaises(DeployError, self.event)

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-install')

  # packages
  # only running these in publish on an ongoing basis to decrease test time
  # suite.addTest(make_extension_suite(TestInstallPackagesEventTestCase,
  #                                     os, version, arch))
  # suite.addTest(packages_mixin_make_suite(TestInstallPackagesEventTestCase,
  #                                         os, version, arch))

  # setup
  suite.addTest(make_extension_suite(TestInstallSetupEventTestCase, os, version, arch))
  suite.addTest(psm_make_suite(TestInstallSetupEventTestCase, os, version, arch))

  # deploy
  suite.addTest(make_extension_suite(TestInstallDeployEventTestCase, os, 
                version, arch, offline=False))
  suite.addTest(Test_ErrorOnDuplicateIds(os, version, arch))
  suite.addTest(Test_CommentsInScripts(os, version, arch))
  suite.addTest(Test_HostnameFile(os, version, arch))
  suite.addTest(Test_SshHost(os, version, arch))
  suite.addTest(Test_ComesBeforeComesAfter(os, version, arch))
  suite.addTest(Test_ReinstallOnReleaseRpmChange(os, version, arch))
  suite.addTest(Test_ReinstallOnConfigRpmChange(os, version, arch))
  suite.addTest(Test_ReinstallOnKickstartChange(os, version, arch))
  suite.addTest(Test_ReinstallOnTreeinfoChange(os, version, arch))
  suite.addTest(Test_ReinstallOnInstallScriptChange(os, version, arch))
  suite.addTest(Test_ReinstallOnPostInstallScriptChange(os, version, arch))
  suite.addTest(Test_ReinstallOnSaveTriggersScriptChange(os, version, arch))
  # dummy test to shutoff vm
  suite.addTest(dm_make_suite(TestInstallDeployEventTestCase, os, version, 
                              arch))

  return suite
