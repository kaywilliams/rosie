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
from centosstudio.errors import CentOSStudioError
from centosstudio.util   import pps

from cstest      import EventTestCase, ModuleTestSuite
from cstest.core import make_core_suite

from cstest.mixins import (psm_make_suite, dm_make_suite, DeployMixinTestCase,
                           check_vm_config)

class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish-setup'

class KickstartEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'kickstart'
  _conf = """<publish>
  <kickstart >
  <include xmlns='http://www.w3.org/2001/XInclude'
           href='%s/../../share/centosstudio/examples/ks.cfg'
           parse='text'/>
  </kickstart>
  </publish>""" % pps.path(__file__).dirname.abspath() 

  def setUp(self):
    EventTestCase.setUp(self)

  def tearDown(self):
    EventTestCase.tearDown(self)

class Test_KickstartIncludesAdditions(KickstartEventTestCase):
  "kickstart includes additional items"

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
   self.tb.dispatch.execute(until=self.event)
   for item in self.event.locals.L_KICKSTART_ADDS:
     self.failUnless(self.event.locals.L_KICKSTART_ADDS[item]['text'] in 
                     self.event.ksfile.read_text())

  def tearDown(self):
    EventTestCase.tearDown(self)


class Test_KickstartFailsOnInvalidInput(KickstartEventTestCase):
  "kickstart fails on invalid input"
  _conf = "<publish><kickstart>invalid</kickstart></publish>"

  def runTest(self):
   self.execute_predecessors(self.event)
   if self.event.cvars['pykickstart-version'] < '1.74' and self.event.cvars['base-info']['version'][:1] >= '6':
     pass # el5 pykickstart can't validate el6 files
   else:
     self.failUnlessRaises(CentOSStudioError, self.event)

  def tearDown(self):
    EventTestCase.tearDown(self)


class PublishEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish'

  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(self.event.cvars['%s-setup-options' % self.moduleid]
                                       ['localpath'])
    EventTestCase.tearDown(self)

class DeployEventTestCase(DeployMixinTestCase):
  moduleid = 'publish'
  eventid  = 'deploy'

  def __init__(self, distro, version, arch, conf=None):
    DeployMixinTestCase.__init__(self, distro, version, arch, conf)

def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('publish')

  # publish-setup
  suite.addTest(make_core_suite(PublishSetupEventTestCase, distro, version, arch))
  suite.addTest(psm_make_suite(PublishSetupEventTestCase, distro, version, arch))

  # kickstart
  suite.addTest(make_core_suite(KickstartEventTestCase, distro, version, arch))
  suite.addTest(Test_KickstartIncludesAdditions(distro, version, arch))
  suite.addTest(Test_KickstartFailsOnInvalidInput(distro, version, arch))

  # publish
  suite.addTest(make_core_suite(PublishEventTestCase, distro, version, arch))

  # deploy
  if check_vm_config():
    suite.addTest(make_core_suite(DeployEventTestCase, distro, version, arch))
    suite.addTest(dm_make_suite(DeployEventTestCase, distro, version, arch))
  return suite
