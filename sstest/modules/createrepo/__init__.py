#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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
from rendition import pps
from rendition.rxml.config import Element

from sbtest      import EventTestCase, ModuleTestSuite
from sbtest.core import make_core_suite


class CreaterepoEventTestCase(EventTestCase):
  moduleid = 'createrepo'
  eventid  = 'createrepo'


class Test_CompsFile(CreaterepoEventTestCase):
  "comps file provided"
  def runTest(self):
    self.tb.dispatch.execute(until='createrepo')
    self.failUnlessExists(self.event.cvars['repodata-directory'] /
                          self.event.cvars['groupfile'].basename)

class Test_SignedRpms(CreaterepoEventTestCase):
  "uses signed rpms when gpgsign is enabled"
  _conf = """<gpgsign>
    <public-key>%s</public-key>
    <secret-key>%s</secret-key>
    <passphrase></passphrase>
  </gpgsign>""" % (pps.path(__file__).dirname.abspath()/'RPM-GPG-KEY-test',
                   pps.path(__file__).dirname.abspath()/'RPM-GPG-SEC-KEY-test')

  def runTest(self):
    self.tb.dispatch.execute(until='createrepo')
    # no need to test anything specifically; if we get this far we succeeded

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('createrepo')

  suite.addTest(make_core_suite(CreaterepoEventTestCase, distro, version, arch))
  suite.addTest(Test_CompsFile(distro, version, arch))
  suite.addTest(Test_SignedRpms(distro, version, arch))

  return suite
