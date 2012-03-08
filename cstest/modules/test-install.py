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

from centosstudio.errors import CentOSStudioError
from centosstudio.util   import pps 
from centosstudio.util   import rxml 

from centosstudio.util.rxml  import datfile 

from centosstudio.modules.shared.deploy import InvalidInstallTriggerError

from cstest      import EventTestCase, ModuleTestSuite
from cstest.core import make_extension_suite

from cstest.mixins import (psm_make_suite, dm_make_suite,
                           check_vm_config)


class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install-setup'

  _conf = [
    """
    <packages>
      <group>core</group>
      <group>base</group>
    </packages>
    """,
    """
    <%(module)s password='password'>
      <kickstart>
      <include 
         xmlns='http://www.w3.org/2001/XInclude'
         href='%(root)s/../../share/centosstudio/examples/common/ks.cfg'
         parse='text'/>
      </kickstart>
      <include 
        xmlns='http://www.w3.org/2001/XInclude'
        href='%(root)s/../../share/centosstudio/examples/common/deploy.xml' 
        xpointer="xpointer(/*/*[name()!='post-script' and 
                                name()!='update-script'])"/>
    </%(module)s>
    """ % {'module'   : moduleid,
           'root'     : pps.path(__file__).dirname.abspath()}]


  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(
        self.event.cvars['%s-setup-options' % self.moduleid]['localpath'])
    EventTestCase.tearDown(self)


class TestInstallEventTestCase(PublishSetupEventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install'

  def __init__(self, distro, version, arch, *args, **kwargs):
    PublishSetupEventTestCase.__init__(self, distro, version, arch, *args, **kwargs)

    # set hostname
    self.hostname = "cstest-%s-%s.local" % (self.version, self.arch)
    self.conf.get("/*/%s" % self.moduleid).set('hostname', self.hostname)

  def setUp(self):
    PublishSetupEventTestCase.setUp(self)

    if not self.event: # module disabled
      return

    # set password and crypt password in datfile
    root = datfile.parse(self.event._config.file).getroot()
    mod = root.get('%s' % self.moduleid, '')
    if len(mod) == 0:
      mod = datfile.uElement('%s' % self.moduleid, parent=root)
    datfile.uElement('crypt-password', text='$6$OJZ6KCfu$GcpaU07JTXN1y/bMSunZJDt.BBMOl1gs7ZoJy1c6No4iJyyXUFhD3X2ar1ZT2qKN/NS9KLDoyczmuIfVyDPiZ/', parent=mod)
    root.write()

  def tearDown(self):
    EventTestCase.tearDown(self) 

class Test_RaisesErrorOnInvalidTriggers(TestInstallEventTestCase):
  "raises an error if invalid triggers are provided"

  def setUp(self):
    TestInstallEventTestCase.setUp(self)
    self.conf.get('/*/%s/trigger-script' % self.moduleid).set(
                  'triggers', 'kickstart, install-script junk1, junk2')

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(InvalidInstallTriggerError, self.event)


class Test_NoReinstall(TestInstallEventTestCase):
  "does not reinstall if triggers unchanged"

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not self.event.cvars.get('%s-reinstalled' % self.moduleid, 
                                            False))


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
    self.event.cvars['rpmbuild-data'][self.event.cvars['release-rpm-name']][
                     'rpm-release'] += '1'
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_ReinstallOnConfigRpmChange(ReinstallTestInstallEventTestCase):
  "reinstalls if config-rpm changes"

  def __init__(self, distro, version, arch, *args, **kwargs):
    ReinstallTestInstallEventTestCase.__init__(self, distro, version, arch, *args, **kwargs)
    self._add_config("""
      <config-rpm>
      <script type='post'>echo 'hello'</script>
      </config-rpm>
      """)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_ReinstallOnKickstartChange(ReinstallTestInstallEventTestCase):
  "reinstalls if kickstart changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.cvars['test-install-kstext'] = ''
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_ReinstallOnTreeinfoChange(ReinstallTestInstallEventTestCase):
  "reinstalls if treeinfo changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.cvars['base-treeinfo-text'] = ''
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_ReinstallOnInstallScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if install-script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    script = self.event.config.get('install-script')
    script.text = 'echo "Hello"'
    self.failUnlessRaises(CentOSStudioError, self.event)


class Test_ReinstallOnPostInstallScriptChange(ReinstallTestInstallEventTestCase):
  "reinstalls if post-install-script changes"

  def runTest(self):
    self.execute_predecessors(self.event)
    script = self.event.config.get('post-install-script')
    script.text = 'echo "hello"'
    self.failUnlessRaises(CentOSStudioError, self.event)


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-install')

  # setup
  suite.addTest(make_extension_suite(PublishSetupEventTestCase, distro, version, arch))
  suite.addTest(psm_make_suite(PublishSetupEventTestCase, distro, version, arch))

  # deploy
  if check_vm_config():
    suite.addTest(make_extension_suite(TestInstallEventTestCase, distro, version, arch))
    suite.addTest(Test_RaisesErrorOnInvalidTriggers(distro, version, arch))
    suite.addTest(Test_NoReinstall(distro, version, arch))
    suite.addTest(Test_ReinstallOnReleaseRpmChange(distro, version, arch))
    suite.addTest(Test_ReinstallOnConfigRpmChange(distro, version, arch))
    suite.addTest(Test_ReinstallOnKickstartChange(distro, version, arch))
    suite.addTest(Test_ReinstallOnTreeinfoChange(distro, version, arch))
    suite.addTest(Test_ReinstallOnInstallScriptChange(distro, version, arch))
    suite.addTest(Test_ReinstallOnPostInstallScriptChange(distro, version, arch))
    suite.addTest(Test_ReinstallOnPostInstallScriptChange(distro, version, arch))
    # dummy test to shutoff vm
    suite.addTest(dm_make_suite(TestInstallEventTestCase, distro, version, arch, ))

  return suite
