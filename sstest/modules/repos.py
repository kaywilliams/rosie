#
# Copyright (c) 2010
# Solution Studio Foundation. All rights reserved.
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
from sstest      import EventTestCase, ModuleTestSuite
from sstest.core import make_core_suite

class ReposEventTestCase(EventTestCase):
  moduleid = 'repos'
  eventid  = 'repos'

class Test_NoBase(ReposEventTestCase):
  "without base-info and repos sections, raises RuntimeError"
  _conf = ["<base/>","<repos/>"]

  def runTest(self):
    try:
      self.tb.dispatch.execute(until='repos')
      # we actually get a runtime error earlier than repos (installer, atm)
    except RuntimeError:
      return
    # if we don't raise a runtime error, we have to fail
    self.fail()
    ##self.failUnlessRaises(RuntimeError, self.event)

class Test_RepoDefaults(ReposEventTestCase):
  "defaults defined in repos section are used"
  _conf = """<repos>
    <repo id="base">
      <baseurl>/nonexistant/path</baseurl>
      <mirrorlist/>
    </repo>
    <repo id="updates">
      <gpgcheck>no</gpgcheck>
    </repo>
    <repo id="everything">
      <enabled>no</enabled>
    </repo>
    <repo id="new">
      <baseurl>/nonexistant/path</baseurl>
    </repo>
  </repos>
  """

  def runTest(self):
    self.execute_predecessors(self.event)
    try:
      self.tb.dispatch.execute(until='repos') # this will raise an exception
    except:
      pass

    # make sure we have the right repos to start wtih
    self.failUnless(self.event.repos.has_key('base'))
    self.failUnless(self.event.repos.has_key('updates'))
    self.failUnless(self.event.repos.has_key('new'))
    self.failIf(self.event.repos.has_key('everything'))

    self.failUnless(self.event.repos['base'].baseurl[0].equivpath('/nonexistant/path'))
    self.failUnless(self.event.repos['base'].mirrorlist is None)
    self.failUnlessEqual(self.event.repos['updates'].gpgcheck, False)

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('repos')

  suite.addTest(make_core_suite(ReposEventTestCase, distro, version, arch))
  suite.addTest(Test_NoBase(distro, version, arch))
  suite.addTest(Test_RepoDefaults(distro, version, arch))

  return suite
