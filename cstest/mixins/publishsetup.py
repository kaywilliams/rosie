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

from centosstudio.errors    import CentOSStudioError
from centosstudio.util.rxml import config, datfile

from cstest      import EventTestCase, decorate
from cstest.core import CoreTestSuite

class PublishSetupMixinTestCase:
  pass

def PublishSetupMixinTest_Config(self):
  self._testMethodDoc = "config values correctly populate macros and cvars"

  self.values = { 
    'password':     'test-password',
    'hostname':     'test-hostname',
    'localpath':    '/test/local/path',
    'webpath':      'http://test/web/path',
    'boot_options': 'test boot options',
    }

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    mod.set("password", self.values['password'])
    mod.set("hostname", self.values['hostname'])
    config.Element('local-dir', text=self.values['localpath'], parent=mod)
    config.Element('remote-url', text=self.values['webpath'], parent=mod)
    config.Element('boot-options', text=self.values['boot_options'], parent=mod)

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(check_results()) 

  def check_results():
    errors = [] 

    # check attributes
    for k in self.values:
      if k in ['webpath', 'localpath']:
        test = eval('self.event.%s' % k).startswith(self.values[k])
      else:
        test = eval('self.event.%s' % k) == self.values[k] 
      if not test: 
        errors.append("%s attribute does not match: %s, %s" % 
                     (k, eval('self.event.%s' % k), self.values[k])) 

    # check macros
    for k in self.values:
      if k == 'localpath':
        continue
      elif k == 'webpath':
        test = self.event.macros['%{url}'].startswith(self.values[k])
      else:
        test = (eval('self.event.macros["%%{%s}"]' % k.replace('_', '-')) 
                == self.values[k])
      if not test:
        errors.append("%s macro does not match: %s, %s" % 
                     (k, eval('self.event.%s' % k), self.values[k])) 


    #check cvars
    for k in self.values:
      if k in ['webpath', 'localpath']:
        test = (eval('self.event.cvars["%s-setup-options"]["%s"]' % 
               (self.moduleid, k)).startswith(self.values[k]))
      else:
        test = (eval('self.event.cvars["%s-setup-options"]["%s"]' % 
               (self.moduleid, k.replace('_', '-'))) == self.values[k])
      if not test:
        errors.append("%s cvar does not match: %s, %s" % 
                     (k, eval('self.event.%s' % k), self.values[k])) 

    if errors:
      print errors
      return False
    else:
      return True

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self

def PublishSetupMixinTest_NoPassword(self):
  self._testMethodDoc = "password generated if not provided"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    mod.attrib.pop("password", '')

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

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self

def PublishSetupMixinTest_Password(self):
  self._testMethodDoc = "password used if provided"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    mod.set("password", "password")

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(self.event.cvars['%s-setup-options' % self.moduleid]
                    ['password'] == 'password')
    self.failUnless(saved(self, 'password/text()') == '')
    self.failUnless(saved(self, 'crypt-password/text()') != '')

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self

def saved(self, xpath):
  return self.event.parse_datfile().getxpath(
                                    '/*/%s/%s' % (self.moduleid, xpath), '')

def psm_make_suite(TestCase, distro, version, arch, conf=None, xpath=None):
  suite = CoreTestSuite()
  suite.addTest(PublishSetupMixinTest_Config(TestCase(distro, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_NoPassword(TestCase(distro, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_Password(TestCase(distro, version, arch, conf)))
  return suite

