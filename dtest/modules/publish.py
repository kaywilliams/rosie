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
from deploy.errors import DeployError
from deploy.util   import pps

from dtest      import EventTestCase, ModuleTestSuite
from dtest.core import make_core_suite

from dtest.mixins import (psm_make_suite, check_vm_config)

class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish-setup'
  _type = 'package'

class KickstartEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'kickstart'
  _conf = [
  """<packages><package>kernel</package></packages>""",
  """<base-info enabled='true'/>""",
  """<publish>
  <include xmlns='http://www.w3.org/2001/XInclude'
           href='%s/../../share/deploy/templates/deploy/ks.xml'/>
  </publish>""" % pps.path(__file__).dirname.abspath()]

  def setUp(self):
    EventTestCase.setUp(self)

  def tearDown(self):
    EventTestCase.tearDown(self)


class Test_KickstartFailsOnInvalidInput(KickstartEventTestCase):
  "kickstart fails on invalid input"
  _conf = ["<packages><package>kernel</package></packages>",
           "<publish><kickstart>invalid</kickstart></publish>"]

  def runTest(self):
   self.execute_predecessors(self.event)
   if self.event.cvars['pykickstart-version'] < '1.74' and self.event.cvars['base-info']['version'][:1] >= '6':
     pass # el5 pykickstart can't validate el6 files
   else:
     self.failUnlessRaises(DeployError, self.event)

  def tearDown(self):
    EventTestCase.tearDown(self)


class PublishEventTestCase(EventTestCase):
  moduleid = 'publish'
  eventid  = 'publish'
  _type = 'package'

  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(self.event.cvars['%s-setup-options' % self.moduleid]
                                       ['localpath'])
    EventTestCase.tearDown(self)


def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('publish')

  # publish-setup
  suite.addTest(make_core_suite(PublishSetupEventTestCase, os, version, arch))
  suite.addTest(psm_make_suite(PublishSetupEventTestCase, os, version, arch))

  # kickstart
  suite.addTest(make_core_suite(KickstartEventTestCase, os, version, arch))
  suite.addTest(Test_KickstartFailsOnInvalidInput(os, version, arch))

  # publish
  suite.addTest(make_core_suite(PublishEventTestCase, os, version, arch))

  return suite
