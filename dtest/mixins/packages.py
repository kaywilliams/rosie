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

from dtest        import EventTestCase, decorate, _run_make
from dtest.core   import CoreTestSuite

from deploy.constants import KERNELS

REPODIR  = (pps.path(__file__).dirname/'../modules/shared').abspath()
_run_make(REPODIR)

class PackagesMixinTestCase(EventTestCase):
  _type = 'package'

  def __init__(self, os, version, arch, *args, **kwargs):
    EventTestCase.__init__(self, os, version, arch, *args, **kwargs)

    conf = self.conf.getxpath(self.moduleid)
    rxml.config.Element(name='group', parent=conf, text='core')
    rxml.config.Element(name='exclude', parent=conf, text='NetworkManager')
    rxml.config.Element(name='package', parent=conf, text='http')


def Test_IncludeFile(self):
  _conf = """<packages>
    <package dir='%s/repo1/RPMS/'>package1</package>
  </packages>""" % REPODIR


  def runTest(self):
    self.tb.dispatch.execute(until=self.event.id)
    self.failUnless('package1-1.0-2.noarch.rpm'
                    in [ x.basename for x in self.event.rpmsdir.listdir() ])


def PackagesMixinTest_CheckResults(self):
  self._testMethodDoc = "cvars populated and package downloaded"

  def pre_setUp():
    conf = self.conf.getxpath(self.moduleid)
    rxml.config.Element(name='package', parent=conf, text='package1',
                        attrib={'dir': '%s/repo1/RPMS' % REPODIR})

  def runTest():
    self.tb.dispatch.execute(until=self.event.id)

    # check user-required groups
    self.failUnless('core' in [ x.text for x in 
                                self.event.cvars['user-required-groups']])

    # check excluded-packages
    self.failUnless('NetworkManager' in self.event.cvars['excluded-packages'])

    # check user-required-packages
    self.failUnless(set(['http', 'package1']) ==
                    self.event.cvars['user-required-packages'])

    # check downloaded packages                
    self.failUnless('package1-1.0-2.noarch.rpm'
                    in [ x.basename for x in self.event.rpmsdir.listdir() ])


  decorate(self, 'setUp', prefn=pre_setUp)
  self.runTest = runTest

  return self


def packages_mixin_make_suite(TestCase, os, version, arch, conf=None, xpath=None):
  suite = CoreTestSuite()
  suite.addTest(PackagesMixinTest_CheckResults(TestCase(os, version, arch, conf)))
  return suite

