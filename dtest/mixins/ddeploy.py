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

from deploy.util      import pps
from deploy.util      import rxml

from dtest        import EventTestCase, decorate
from dtest.core   import CoreTestSuite

from publishsetup import PublishSetupMixinTestCase

__all__ = ['DeployMixinTestCase', 'dm_make_suite']

class DeployMixinTestCase(PublishSetupMixinTestCase):
  _type = 'system'
  
  def __init__(self, os, version, arch, module=None, 
               iso=False, iso_location=None):
    self.deploy_module = module or self.moduleid
    self.iso = iso
    self.iso_location = iso_location

    PublishSetupMixinTestCase.__init__(self, os, version, arch,
                                       deploy_module=self.deploy_module)

    # ensure deploy_module element exists
    mod = self.conf.getxpath('/*/%s' % self.deploy_module, None)
    if mod is None:
      mod = rxml.config.Element('%s' % self.deploy_module, parent=self.conf)

    # add dummy kickstart element so kickstart event doesn't disable itself
    # this is technically only necessary when deploy_module == publish
    self.kickstart_added=False
    if not mod.getxpath('kickstart', None):
      rxml.config.Element(name='kickstart', parent=mod, text='dummy')
      self.kickstart_added=True

    # add dummy script element so deploy event doesn't disable itself
    # this is technically only necessary when deploy_module == publish
    self.script_added=False
    if not mod.xpath('script', []):
      rxml.config.Element(name='script', parent=mod, text='dummy',
                          attrib={'id':'dummy', 'type':'post'})
      self.script_added=True

  def setUp(self):
    EventTestCase.setUp(self)

    # get default deploy config
    self.macros = self.tb.initial_macros 

    self.macros.update({
              '%{name}'     : self.tb.name,
              '%{version}'  : self.tb.version,
              '%{arch}'     : self.tb.arch,
              '%{id}'       : self.tb.id,
              '%{file-size}': '6',
              '%{definition-dir}': self.tb.definition_path.dirname,
              '%{data-dir}' : self.tb.data_dir,
              '%{module}'   : self.deploy_module
              })

    deploy = rxml.config.parse(
      '%s/../../share/deploy/templates/%s/libvirt/deploy.xml' %  
      (pps.path(__file__).dirname.abspath(), self.norm_os),
      xinclude = True,
      macros = self.macros,
      ).getroot()

    if self.iso:
      self._iso_install_script(deploy, self.iso_location)

    deploy.remove_macros()

    # update module
    mod = self.tb.definition.getxpath('/*/%s' % self.deploy_module, None)

    # remove dummy elements added by __init__()
    self.kickstart_added and mod.remove(mod.getxpath('kickstart'))
    self.script_added and mod.remove(mod.getxpath('script[@id="dummy"]'))

    if mod.getxpath('password', None) is not None:
      rxml.config.Element(name='password', parent=mod, text='dtest')

    if self.deploy_module != 'test-install':
      triggers = rxml.config.Element('triggers', parent=mod)
      triggers.text = 'kickstart install_scripts'

    mod.extend(deploy.xpath("/*/*[name()!='script']"))
    mod.extend(deploy.xpath("/*/script[@id!='post']"))

  def runTest(self):
    if self.deploy_module == 'publish': event = 'deploy'
    else: event = self.deploy_module

    self.tb.dispatch.execute(until=event)

  def _iso_install_script(self, root, location):
    """
    updates deploy element with text of a script for performing libvirt 
    installation given the relative path to an iso file
    """
  
    install_script = root.getxpath('script[@id="install"]')
    for elem in install_script.getchildren():
      install_script.remove(elem)
    install_script.text = """
#!/bin/sh
set -e

%%{source-guestname}

deploydir="/var/lib/deploy/deploy/%%{id}"
file=$deploydir/$(basename %(location)s)
wget -q -O $file %(location)s
chcon -t httpd_sys_content_t $file

virt-install \
             --name $guestname \
             --arch %%{arch} \
             --ram 1000 \
             --network network=deploy \
             --graphics vnc \
             --disk path=/var/lib/libvirt/images/$guestname.img,size=6 \
             --cdrom  $file \
             --noreboot

# wait for install to complete and machine to shutdown
while [[ `/usr/bin/virsh domstate $guestname` = "running" ]]; do
  sleep 2
done
    """ % {'location': '%%{os-url}/%s' % location}

    root.resolve_macros(map=self.macros)

def DeployMixinTest_Teardown(self):
  self._testMethodDoc = "dummy test to delete virtual machine"

  def setUp():
    DeployMixinTestCase.setUp(self)
    mod = self.tb.definition.getxpath('/*/%s' % self.deploy_module, None)
    mod = prepare_deploy_elem_to_remove_vm(mod)

  self.setUp = setUp

  return self

def dm_make_suite(TestCase, os, version, arch):
  suite = CoreTestSuite()
  suite.addTest(DeployMixinTest_Teardown(TestCase(os, version, arch)))
  return suite

def prepare_deploy_elem_to_remove_vm(elem):
  """ 
  accepts a deploy elem (publish, test-update or test-install)
  and massages it to to remove an existing virtual machine on the
  next run
  """
  for script in elem.xpath('script[@id!="create-guestname" and '
                                 '@id!="delete"]'):
    elem.remove(script)
  elem.getxpath('script[@id="delete"]').attrib['type'] = 'post'
  elem.getxpath('script[@id="delete"]').attrib['hostname'] = 'localhost'

  return elem

