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
import unittest

from lxml import etree

from deploy.errors    import DeployError
from deploy.util      import pps
from deploy.util      import rxml
from deploy.util.rxml import config

from dtest        import EventTestCase, decorate
from dtest.core   import CoreTestSuite

class PublishSetupMixinTestCase(EventTestCase):
  def __init__(self, os, version, arch, deploy_module=None, **kwargs):
    EventTestCase.__init__(self, os, version, arch)
    self.deploy_module = deploy_module
    if not self.deploy_module:
      if self.moduleid in ['test-install', 'test-update']:
        self.deploy_module = self.moduleid
      else:
        self.deploy_module = 'publish'
    decorate(self, 'tearDown', prefn=self.pre_teardown)

    # update packages
    pkgcontent=etree.XML("""
    <packages xmlns:xi='%s'>
      <xi:include href="%%{templates-dir}/%%{norm-os}/common/packages.xml"
                  xpointer="xpointer(./packages[@id='core']/*)"/>
    </packages>""" % rxml.tree.XI_NS)
    packages = self.conf.getxpath('/*/packages', None)
    if packages is None:
      packages = rxml.config.Element('packages', parent=self.conf)
    packages.extend(pkgcontent.xpath('/*/*'))

  def pre_teardown(self):
    # 'register' publish_path for deletion upon test completion
    self.output.append(self.event.cvars['%s-setup-options' % self.deploy_module]
                                       ['localpath'])

def PublishSetupMixinTest_Config(self):
  self._testMethodDoc = "config values correctly populate macros and cvars"

  self.values = { 
    'password':       'test-password',
    'hostname':       'test-hostname',
    'domain':         '.test-domain',
    'fqdn':           'test-hostname.test-domain',
    'localpath':      '/test/local/path',
    'build_host':     'test',
    'webpath':        'http://test/web/path',
    'boot_options':   'test boot options',
    }

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    for item in ['hostname', 'password', 'domain', 'remote-url', 'build-host']:
      elem = self.conf.getxpath('/*/%s/%s' % (self.moduleid, item), None)
      if elem is not None: mod.remove(elem)
    config.Element('hostname', text=self.values['hostname'], parent=mod)
    config.Element('domain', text=self.values['domain'], parent=mod)
    config.Element('password', text=self.values['password'], parent=mod)
    config.Element('local-dir', text=self.values['localpath'], parent=mod)
    config.Element('build-host', text=self.values['build_host'], parent=mod)
    config.Element('remote-url', text=self.values['webpath'], parent=mod)
    config.Element('boot-options', text=self.values['boot_options'], parent=mod)

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(check_results()) 

  def check_results():
    errors = [] 

    # check elements
    for k in self.values:
      if k in ['webpath', 'localpath']:
        test = eval('self.event.%s' % k).startswith(self.values[k])
      else:
        test = eval('self.event.%s' % k) == self.values[k] 
      if not test: 
        errors.append("%s element does not match: %s, %s" % 
                     (k, eval('self.event.%s' % k), self.values[k])) 

    # check macros
    for k in self.values:
      if k in ['localpath', 'build_host']:
        continue
      elif k in [ 'webpath']:
        test = ( self.event.map["%{webroot}"] == pps.path(self.values[k]) / 
                                                 self.event.build_id )
      else:
        test = (eval('self.event.map["%%{%s}"]' % k.replace('_', '-')) 
                == self.values[k])
      if not test:
        errors.append("%s macro does not match: %s, %s" % 
                     (k, eval('self.event.%s' % k), self.values[k])) 


    #check cvars
    for k in self.values:
      if k in ['webpath', 'localpath']:
        test = (eval('self.event.cvars["%s-setup-options"]["%s"]' % 
               (self.moduleid, k.replace('_', '-'))).startswith(self.values[k]))
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

def PublishSetupMixinTest_LongHostname(self):
  self._testMethodDoc = "hostname segment exceeds 255 characters"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    elem = self.conf.getxpath('/*/%s/hostname' % (self.moduleid), None)
    if elem is not None: mod.remove(elem)
    config.Element('hostname', parent=mod, 
                   text=( "thishostnameisover255characters.thishostnameisover"
                          "255.charactersthishostnameisover255characters.this"
                          "hostnameisover255characters.thishostnameisover255"
                          "characters.thishostnameisover255characters.this"
                          "hostnameisover255characters.thishostnameisover255"
                          "characters.thishostnameisover255characters.this"
                          "hostnameisover255characters.thishostnameisover255"))

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event) 

  def tearDown():
    EventTestCase.tearDown(self)

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest
  self.tearDown = tearDown 

  return self

def PublishSetupMixinTest_LongHostnameSegment(self):
  self._testMethodDoc = "hostname segment exceeds 63 characters"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    elem = self.conf.getxpath('/*/%s/hostname' % (self.moduleid), None)
    if elem is not None: mod.remove(elem)
    config.Element('hostname', parent=mod, 
                   text=( "thishostnamesegmentisover63charactersthishostname"
                          "segmentisover63characters" ))

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event) 

  def tearDown():
    EventTestCase.tearDown(self)

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest
  self.tearDown = tearDown 

  return self

def PublishSetupMixinTest_HostnameLeadingHyphen(self):
  self._testMethodDoc = "hostname segment has leading hyphen"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    elem = self.conf.getxpath('/*/%s/hostname' % (self.moduleid), None)
    if elem is not None: mod.remove(elem)
    config.Element('hostname', parent=mod, text="-hostname") 

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)

  def tearDown():
    EventTestCase.tearDown(self)

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest
  self.tearDown = tearDown 

  return self

def PublishSetupMixinTest_HostnameTrailingHyphen(self):
  self._testMethodDoc = "hostname segment has trailing hyphen"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    elem = self.conf.getxpath('/*/%s/hostname' % (self.moduleid), None)
    if elem is not None: mod.remove(elem)
    config.Element('hostname', parent=mod, text="hostname-")

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event) 

  def tearDown():
    EventTestCase.tearDown(self)

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest
  self.tearDown= tearDown 

  return self

def PublishSetupMixinTest_HostnameInvalidCharacters(self):
  self._testMethodDoc = "hostname segment contains invalid characters"

  def pre_setUp():
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    elem = self.conf.getxpath('/*/%s/hostname' % (self.moduleid), None)
    if elem is not None: mod.remove(elem)
    config.Element('hostname', parent=mod, text="host%name")

  def runTest():
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event) 

  def tearDown():
    EventTestCase.tearDown(self)

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest
  self.tearDown = tearDown 

  return self

def PublishSetupMixinTest_NoPassword(self):
  self._testMethodDoc = "password generated if not provided"

  def pre_setUp():
    password = self.conf.getxpath('/*/%s/password' % self.moduleid, None)
    if password is not None: password.getparent().remove(password) 

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(self.event.password 
                    and self.event.password == saved(self, 
                        'generated-password/text()') 
                    and len(saved(self, 'user-password/text()')) == 0
                    and len(saved(self, 'crypt-password/text()')) > 0 )

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self

def PublishSetupMixinTest_Password(self):
  self._testMethodDoc = "password used if provided"

  def pre_setUp():
    password = self.conf.getxpath('/*/%s/password' % self.moduleid, None)
    if password is not None: password.getparent().remove(password)
 
    mod = self.conf.getxpath('/*/%s' % self.moduleid, None)
    config.Element('password', text='password', parent=mod)

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless(self.event.cvars['%s-setup-options' % self.moduleid]
                    ['password'] == 'password')
    self.failUnless(saved(self, 'user-password/text()') == 'password')

  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self

def saved(self, xpath):
  return self.event.parse_datfile().getxpath(
                                    '/*/%s/%s' % (self.moduleid, xpath), '')

def psm_make_suite(TestCase, os, version, arch, conf=None, xpath=None):
  suite = CoreTestSuite()
  suite.addTest(PublishSetupMixinTest_Config(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_LongHostname(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_LongHostnameSegment(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_HostnameLeadingHyphen(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_HostnameTrailingHyphen(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_HostnameInvalidCharacters(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_NoPassword(TestCase(os, version, arch, conf)))
  suite.addTest(PublishSetupMixinTest_Password(TestCase(os, version, arch, conf)))
  return suite

