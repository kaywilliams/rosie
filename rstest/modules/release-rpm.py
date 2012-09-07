#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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

from repostudio.errors   import CentOSStudioError
from repostudio.util     import pps
from repostudio.util     import repo
from repostudio.util     import rxml
from repostudio.util.pps.constants import TYPE_NOT_DIR

from rstest          import (BUILD_ROOT, TestBuild, EventTestCase, 
                            ModuleTestSuite)
from rstest.core     import make_core_suite
from rstest.mixins   import (MkrpmRpmBuildMixinTestCase, RpmCvarsTestCase,
                             DeployMixinTestCase, check_vm_config, 
                             dm_make_suite)


class ReleaseRpmEventTestCase(MkrpmRpmBuildMixinTestCase, EventTestCase):
  moduleid = 'release-rpm'
  eventid  = 'release-rpm'
  _type = 'package' 

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')

    base = repo.getDefaultRepoById('base', distro=self.distro,
                                           version=self.version,
                                           arch=self.arch,
                                           include_baseurl=True,
                                           baseurl='http://www.repostudio.org/mirrors/%s' % self.distro)
    base.update({'mirrorlist': None, 'gpgcheck': None, 'name': None,})

    repos.append(base.toxml()) # don't overwrite gpgkey and gpgcheck defaults

    return repos

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
    self.failUnless((self.event.REPO_STORE/'gpgkeys').findpaths(mindepth=1))
    expected = [ x.basename for x in self.event.cvars['gpgkeys'] ]
    expected.append('gpgkey.list')
    found = [ x.basename for x in
             (self.event.REPO_STORE/'gpgkeys').findpaths(mindepth=1,
                                                             type=TYPE_NOT_DIR)]
    self.failUnless(expected)
    self.failUnless(set(expected) == set(found))

class Test_RemovesGpgkeys(ReleaseRpmEventTestCase):
  "removes output when gpgcheck disabled"
  _conf = """<release-rpm>
    <updates gpgcheck='false'/>
  </release-rpm>"""

  def _make_repos_config(self):
    return ReleaseRpmEventTestCase._make_repos_config(self)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless(not (self.event.REPO_STORE/'gpgkeys').
                         findpaths())

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

  def __init__(self, distro, version, arch, *args, **kwargs):
    DeployMixinTestCase.__init__(self, distro, version, arch, module='publish')

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
    files.text = ' '.join(self.event.cvars['gpgkey-ids']).lower()
    self.tb.dispatch.get('config-rpm').status = True # force config-rpm

    # set post script for deploy - doing this after repostudio
    # resolves global macros on the definition so macro replacement 
    # doesn't blast the rpm qf string (%{version})
    publish = self.event._config.getxpath('/*/publish')
    post = publish.getxpath('post', rxml.config.Element('post', parent=publish))
    post_script = rxml.config.Element('script', attrs={'id':'release-rpm'})
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

def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('release-rpm')

  suite.addTest(make_core_suite(ReleaseRpmEventTestCase, distro, version, arch))
  suite.addTest(Test_ReleaseRpmBuild(distro, version, arch))
  suite.addTest(Test_ReleaseRpmCvars1(distro, version, arch))
  suite.addTest(Test_ReleaseRpmCvars2(distro, version, arch))
  suite.addTest(Test_OutputsGpgkeys(distro, version, arch))
  suite.addTest(Test_RemovesGpgkeys(distro, version, arch))

  if check_vm_config():
    suite.addTest(Test_TestMachineSetup(distro, version, arch))
    suite.addTest(Test_GpgkeysInstalled(distro, version, arch))
    # dummy test to shutoff vm
    suite.addTest(dm_make_suite(DeployReleaseRpmEventTestCase, distro, version, arch, ))


  return suite