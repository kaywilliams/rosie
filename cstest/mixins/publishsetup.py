#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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

from centosstudio.util.rxml import datfile

from cstest      import EventTestCase, decorate
from cstest.core import CoreTestSuite

class PublishSetupMixinTestCase:
  pass

def PSMTest_NoPassword(self):
  self._testMethodDoc = "password generated if not provided"

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    # print "password: ", self.event.password
    # print "saved password: ", saved(self, 'password/text()')
    # print "saved cryptpw: ", saved(self, 'crypt-password/text()')
    # print "saved elem: ", saved(self, '.')
    if self.moduleid == 'publish':
      additional_tests = self.event.password == saved(self, 'password/text()') \
                         and len(saved(self, 'crypt-password/text()')) > 0 
    else:
      additional_tests = len(saved(self, '.')) == 0

    self.failUnless(self.event.password and additional_tests) 

  self.runTest = runTest

  return self

def PSMTest_Password(self):
  self._testMethodDoc = "password used if provided"

  def pre_setUp():
    mod = self.conf.get('/*/%s' % self.moduleid, None)
    if mod is not None:
      mod.set("password", "password")
    else:
      self._add_config("<%s password='password'/>" % self.moduleid)

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    # print "password: ", self.event.password
    # print "saved password: ", saved(self, 'password/text()')
    # print "saved cryptpw: ", saved(self, 'crypt-password/text()')
    self.failUnless(self.event.password == 'password' and 
                                    saved(self, 'password/text()') == '' and
                                    saved(self, 'crypt-password/text()') != '')

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self

def saved(self, xpath):
  return datfile.parse(self.event._config.file).getroot().get(
                                     '/*/%s/%s' % (self.moduleid, xpath), '')

def psm_make_suite(TestCase, distro, version, arch, conf=None, xpath=None):
  suite = CoreTestSuite()
  suite.addTest(PSMTest_NoPassword(TestCase(distro, version, arch, conf)))
  suite.addTest(PSMTest_Password(TestCase(distro, version, arch, conf)))
  return suite

