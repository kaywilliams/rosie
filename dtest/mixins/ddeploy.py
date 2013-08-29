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
import re
import unittest

from lxml import etree

from deploy.util      import pps
from deploy.util      import rxml

from dtest        import EventTestCase, decorate
from dtest.core   import CoreTestSuite

from publishsetup import PublishSetupMixinTestCase

__all__ = ['DeployMixinTestCase', 'dm_make_suite']

class DeployMixinTestCase(PublishSetupMixinTestCase):
  _type = 'system'
  
  def __init__(self, os, version, arch, module=None):
    self.deploy_module = module or self.moduleid
    PublishSetupMixinTestCase.__init__(self, os, version, arch,
                                       deploy_module=self.deploy_module)

    # get default deploy config
    macros = parse_option_macros(self.options.macros) 

    macros.update({
              '%{name}'     : self.name,
              '%{version}'  : version,
              '%{arch}'     : arch,
              '%{id}'       : self.id,
              '%{file-size}': '6',
              '%{definition-dir}': self.definition_path.dirname,
              '%{templates-dir}': self.templates_dir,
              '%{data-dir}': pps.path(self.options.data_root) / self.id
              })

    deploy = rxml.config.parse(
      '%s/../../share/deploy/templates/libvirt/deploy.xml' %  
      pps.path(__file__).dirname.abspath(),
      xinclude = True,
      macros = macros
      ).getroot()

    # update packages
    pkgcontent=etree.XML("""
    <packages>
      <group>core</group>
      <!--add NM as a workaround RTNETLINK/NOZEROCONF issue in el5-->
      <package>NetworkManager</package>
    </packages>""")
    packages = self.conf.getxpath('/*/packages', None)
    if packages is None:
      packages = rxml.config.Element('packages', parent=self.conf)
    packages.extend(pkgcontent.xpath('/*/*'))

    # update module
    mod = self.conf.getxpath('/*/%s' % self.deploy_module, None)
    if mod is None:
      mod = rxml.config.Element('%s' % self.deploy_module, parent=self.conf)

    if self.deploy_module != 'test-install':
      triggers = rxml.config.Element('triggers', parent=mod)
      triggers.text = 'kickstart install_scripts'

    mod.extend(deploy.xpath("/*/*[name()!='script']"))
    mod.extend(deploy.xpath("/*/script[@id!='post']"))
  

  def runTest(self):
    self.tb.dispatch.execute(until='deploy')


def DeployMixinTest_Teardown(self):
  self._testMethodDoc = "dummy test to delete virtual machine"

  def setUp():
    mod = self.conf.getxpath('/*/%s' % self.deploy_module, None)
    mod = prepare_deploy_elem_to_remove_vm(
          mod, parse_option_macros(self.options.macros).get(
          '%{deploy-host}', None))
    EventTestCase.setUp(self)

  self.setUp = setUp

  return self

def dm_make_suite(TestCase, os, version, arch):
  suite = CoreTestSuite()
  suite.addTest(DeployMixinTest_Teardown(TestCase(os, version, arch)))
  return suite

def parse_option_macros(macro_list):
  macros = {}
  for name, value in [ x.split(':') for x in macro_list ]:
    macros['%%{%s}' % name] = value
  return macros

def prepare_deploy_elem_to_remove_vm(elem, deploy_host):
  """ 
  accepts a deploy elem (publish, test-update or test-install)
  and massages it to to remove an existing virtual machine on the
  next run
  """
  for script in elem.xpath('script[@id!="create-guestname" and '
                                 '@id!="delete"]'):
    elem.remove(script)
  elem.getxpath('script[@id="delete"]').attrib['type'] = 'post'
  elem.getxpath('script[@id="delete"]').attrib['hostname'] = (
                                        deploy_host or 'localhost')

  return elem
