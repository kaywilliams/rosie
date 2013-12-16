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
import pykickstart 
import unittest
from deploy.errors import DeployError
from deploy.util   import pps
from deploy.util   import repo
from deploy.util   import rxml

from deploy.util.pps.constants import TYPE_NOT_DIR

from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_core_suite

from dtest.mixins import (psm_make_suite, 
                          PublishSetupMixinTestCase,
                          MkrpmRpmBuildMixinTestCase, RpmCvarsTestCase,
                          DeployMixinTestCase, dm_make_suite)

class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish-setup'
  _type = 'package'


class ReleaseRpmEventTestCase(MkrpmRpmBuildMixinTestCase, EventTestCase):
  moduleid = 'publish'
  eventid  = 'release-rpm'
  _type = 'package' 


class Test_ReleaseRpmBuild(ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_header()

class Test_ReleaseRpmCvars1(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.clean_event_md()
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()

class Test_ReleaseRpmCvars2(RpmCvarsTestCase, ReleaseRpmEventTestCase):
  def setUp(self):
    ReleaseRpmEventTestCase.setUp(self)
    self.event.status = True

  def runTest(self):
    self.tb.dispatch.execute(until='release-rpm')
    self.check_cvars()

class Test_OutputsGpgkeys(ReleaseRpmEventTestCase):
  "creates output when gpgcheck enabled"
  def _make_repos_config(self):
    return ReleaseRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless((self.event.OUTPUT_DIR/'gpgkeys').findpaths(mindepth=1))
    expected = [ x.basename for x in self.event.gpgkeys ]
    expected.append('gpgkey.list')
    found = [ x.basename for x in
             (self.event.OUTPUT_DIR/'gpgkeys').findpaths(mindepth=1,
                                                             type=TYPE_NOT_DIR)]
    self.failUnless(expected)
    self.failUnless(set(expected) == set(found))

class Test_RemovesGpgkeys(ReleaseRpmEventTestCase):
  "removes output when gpgcheck disabled"
  _conf = """<publish><release-rpm>
    <updates gpgcheck='false'/>
  </release-rpm></publish>"""

  def _make_repos_config(self):
    return ReleaseRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not (self.event.OUTPUT_DIR/'gpgkeys').
                         findpaths())

class Test_RemovesSyncPlugin(ReleaseRpmEventTestCase):
  "removes output when sync plugin disabled"
  _conf = """<publish><release-rpm>
    <updates sync='false'/>
  </release-rpm></publish>"""

  def _make_repos_config(self):
    return ReleaseRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not
                   (self.event.rpm.source_folder/'usr/lib/yum-plugins/sync.py').
                    exists())

class DeployReleaseRpmEventTestCase(DeployMixinTestCase, 
                                    ReleaseRpmEventTestCase):
  _conf = 'system'
  _conf = ["""
    <config-rpms>
      <config-rpm id='config'>
      <files destdir='/root' destname='keyids' content='text'>
      dummy text - to be replaced at runtime
      </files>
      </config-rpm>
    </config-rpms>
    """]

  def __init__(self, os, version, arch, *args, **kwargs):
    DeployMixinTestCase.__init__(self, os, version, arch, module='publish')

class Test_TestMachineSetup(DeployReleaseRpmEventTestCase):
  "setting up an initial test machine"


class Test_GpgkeysInstalled(DeployReleaseRpmEventTestCase):
  "expected gpgkeys are installed"

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
   
    # update config-rpm files text to contain keyids 
    # keyids change across test runs, so if keys are not updating
    # properly you will see an error during the next run. This should
    # be improved so that issues appear during the same run...
    files = self.event._config.getxpath('/*/config-rpms/config-rpm/files')
    files.text = ' '.join(self.event.keyids).lower()
    self.tb.dispatch.get('config-rpm').status = True # force config-rpm

    # set post script for deploy - doing this after deploy
    # resolves global macros on the definition so macro replacement 
    # doesn't blast the rpm qf string (%{version})
    publish = self.event._config.getxpath('/*/publish')
    post = publish.getxpath('post', rxml.config.Element('post', parent=publish))
    post_script = rxml.config.Element('script', attrib={'id':'release-rpm'})
    post_script.text = """ 
      #!/bin/bash
      set -e
      installed=`rpm -q gpg-pubkey --qf '%{version} '`
      for expected in `cat /root/keyids`; do
        [[ $installed == *$expected* ]] || echo \
"Error: a key listed in the keyids file is not installed:
expected:  $expected
installed: $installed" >&2
      done
      """

    post.append(post_script)
    self.tb.dispatch.execute(until='deploy')


class KickstartEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'kickstart'
  _conf = [
  """<packages><package>kernel</package></packages>""",
  """<base-info enabled='true'/>""",
  """<publish/>""",]
  
  def __init__(self, os, version, arch, *args, **kwargs):
    EventTestCase.__init__(self, os, version, arch)

    xinclude = rxml.config.fromstring("""
<include xmlns='http://www.w3.org/2001/XInclude'
         href='%s/../../share/deploy/templates/%s/common/ks.xml'/>
""" % (pps.path(__file__).dirname.abspath(), self.norm_os))

    self.conf.getxpath('publish').append(xinclude)

  def setUp(self):
    EventTestCase.setUp(self)

  def tearDown(self):
    EventTestCase.tearDown(self)


class Test_KickstartFailsOnInvalidInput(KickstartEventTestCase):
  "kickstart fails on invalid input"
  _conf = ["<packages><package>kernel</package></packages>",
           "<publish><kickstart>invalid</kickstart></publish>"]

  def __init__(self, os, version, arch, *args, **kwargs):
    EventTestCase.__init__(self, os, version, arch)

  def runTest(self):
   self.execute_predecessors(self.event)
   self.event.setup()
   try:
     exec(self.event.locals.L_PYKICKSTART % {'ksver' : self.event.ksver,
                                             'ksfile': self.event.ksfile})
     self.failUnlessRaises(DeployError, self.event)
   except pykickstart.errors.KickstartVersionError: 
     # todo - use a unittest info log mechanism, if available
     print ("pykickstart on the test system doesn't support '%s' "
            "... skipping test" % self.event.ksver)

  def tearDown(self):
    EventTestCase.tearDown(self)


class PublishEventTestCase(PublishSetupMixinTestCase, EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish'
  _type = 'package'


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('publish')

  # publish-setup
  suite.addTest(make_core_suite(PublishSetupEventTestCase, os, version, arch))
  suite.addTest(psm_make_suite(PublishSetupEventTestCase, os, version, arch))

  # release-rpm
  suite.addTest(make_core_suite(ReleaseRpmEventTestCase, os, version, arch))
  suite.addTest(Test_ReleaseRpmBuild(os, version, arch))
  suite.addTest(Test_ReleaseRpmCvars1(os, version, arch))
  suite.addTest(Test_ReleaseRpmCvars2(os, version, arch))
  suite.addTest(Test_OutputsGpgkeys(os, version, arch))
  suite.addTest(Test_RemovesGpgkeys(os, version, arch))
  suite.addTest(Test_RemovesSyncPlugin(os, version, arch))

  suite.addTest(Test_TestMachineSetup(os, version, arch))
  suite.addTest(Test_GpgkeysInstalled(os, version, arch))
  # dummy test to shutoff vm
  suite.addTest(dm_make_suite(DeployReleaseRpmEventTestCase, os, version, arch, ))

  # kickstart
  suite.addTest(make_core_suite(KickstartEventTestCase, os, version, arch))
  suite.addTest(Test_KickstartFailsOnInvalidInput(os, version, arch))

  # publish
  suite.addTest(make_core_suite(PublishEventTestCase, os, version, arch, 
                offline=False))

  return suite
