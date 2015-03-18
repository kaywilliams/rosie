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

    # include deploy.xml
    mod.append(etree.XML("""
    <include href="%{templates-dir}/%{norm-os}/libvirt/deploy.xml"
             xpath="./*"/>
    """))

  def setUp(self):
    EventTestCase.setUp(self)

    # edit the definition after it has been parsed and deploy.xml included
    mod = self.tb.definition.getxpath('/*/%s' % self.deploy_module, None)

    if self.iso:
      self._iso_install_script(mod, self.iso_location)

    if mod.getxpath('password', None) is None:
      rxml.config.Element(name='password', parent=mod, text='dtest')

  def runTest(self):
    if self.deploy_module == 'publish': event = 'deploy'
    else: event = self.deploy_module

    self.tb.dispatch.execute(until=event)

  def _iso_install_script(self, root, location):
    """
    updates deploy element with text of a script for performing libvirt 
    installation given the relative path to an iso file
    """
    location = pps.path(location)
    imagedir = pps.path('/var/lib/libvirt/images')
    image    = location.basename
    install_script = root.getxpath('script[@id="install"]')

    lines = []
    for line in install_script.text.split('\n'):
      # copy iso to default libvirt storage folder to prevent image from
      # being auto mounted and new xml files from being autogenerated 
      # in /etc/libvirt/storage (el7).
      if '# install machine' in line:
        lines.append('# copy iso to libvirt default storage folder')
        lines.append('cd %s' % imagedir)
        lines.append('cp -a %%{localroot}/%s %s' % (location, imagedir/image))
        lines.append('cd $OLDPWD')
        lines.append('\n')

      # use boot args from image
      if '--extra-args' in line: continue

      # replace '--location' with '--cdrom'
      if '--location' in line:
        line = "--cdrom %s \\" % (imagedir/image)

      lines.append(line)

    # delete image
    lines.append("\n")
    lines.append("# delete image")
    lines.append("rm -f %s" % (imagedir/image))

    install_script.text = '\n'.join(lines)

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
  elem.getxpath('script[@id="delete"]').attrib['modules'] = ('test-install, '
                                                             'test-update, '
                                                             'publish')

  return elem

