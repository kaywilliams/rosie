#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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

from cstest      import EventTestCase, ModuleTestSuite
from cstest.core import make_extension_suite

from cstest.mixins import psm_make_suite

SCRIPTS = """<activate-script>echo "in activate script"</activate-script>
  <delete-script>echo "in delete script"</delete-script>
  <install-script>echo "in install script"</install-script>
  <verify-install-script ssh='no'>echo "in verify-install-script"</verify-install-script>"""

class PublishSetupEventTestCase(EventTestCase):
  moduleid = 'test-install'
  eventid  = 'test-install-setup'

  _conf = """<test-install>
  <kickstart></kickstart>
  %s
  </test-install>""" % SCRIPTS

  def tearDown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(
        self.event.cvars['%s-setup-options' % self.moduleid]['localpath'])
    EventTestCase.tearDown(self)

# TODO - move into shared module
class Test_KickstartIncludesAdditions(PublishSetupEventTestCase):
  "kickstart includes additional items"

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
   self.tb.dispatch.execute(until=self.event)
   for item in self.event.locals.L_KICKSTART_ADDS:
     self.failUnless(self.event.locals.L_KICKSTART_ADDS[item]['text'] in 
                     self.event.ksfile.read_text())


# TODO - move into shared module
class Test_KickstartFailsOnInvalidInput(PublishSetupEventTestCase):
  "kickstart fails on invalid input"
  _conf = "<test-install><kickstart>invalid</kickstart>%s</test-install>" % (
          SCRIPTS)

  def runTest(self):
   self.execute_predecessors(self.event)
   if self.event.cvars['pykickstart-version'] < '1.74' and self.event.cvars['base-info']['version'][:1] >= '6':
     pass # el5 pykickstart can't validate el6 files
   else:
     self.failUnlessRaises(CentOSStudioError, self.event)


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('test-install')

  # setup
  suite.addTest(make_extension_suite(PublishSetupEventTestCase, distro, version, arch))
  suite.addTest(psm_make_suite(PublishSetupEventTestCase, distro, version, arch))
  suite.addTest(Test_KickstartIncludesAdditions(distro, version, arch))
  suite.addTest(Test_KickstartFailsOnInvalidInput(distro, version, arch))


  return suite
