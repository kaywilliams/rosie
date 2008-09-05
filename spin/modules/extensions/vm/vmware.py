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
"""
vmware.py

Convert a libvirt appliance into a vmware appliance.
"""

from rendition import rxml
from rendition import shlib

from spin.constants import KERNELS
from spin.event     import Event

MODULE_INFO = dict(
  api    = 5.0,
  events = ['VmwareVMEvent'],
)

class VmwareVMEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'vmware',
      parentid = 'vm',
      provides = ['vmware-image'],
      requires = ['virtimage-conf', 'virtimage-raw-disk-images'],
    )

    self.vmdir = self.mddir / 'vms'

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [self.vmdir],
      'variables': ['applianceid', 'version', 'fullname',
                    'cvars[\'virtimage-conf\']',
                    'cvars[\'virtimage-raw-disk-images\']'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    # add the virtimage conf to our inputs
    self.DATA['input'].append(self.cvars['virtimage-conf'])

    self.vmdir.mkdirs()

  def run(self):

    # copy image
    for img in self.cvars['virtimage-raw-disk-images']:
      img.cp(self.vmdir, link=True)

    # copy and modify config so virt-pack doesn't error
    vxml = rxml.tree.read(self.cvars['virtimage-conf'])
    vxml.get('name').attrib['version'] = self.version
    rxml.tree.Element('description', text=self.fullname, parent=vxml)
    vxml.write(self.vmdir/'%s.xml' % self.applianceid)

    # convert
    cmd = ( '/usr/bin/virt-pack'
            + ' "%s" ' % (self.vmdir/self.cvars['virtimage-conf'].basename)
            + ' --output "%s"' % self.vmdir )

    shlib.execute(cmd)

    # remove originals, tgz, and xml
    for img in self.cvars['virtimage-raw-disk-images']:
      (self.vmdir/img.basename).remove()
    (self.vmdir/'%s.xml' % self.applianceid).remove()
    (self.vmdir/'%s-%s.tgz' % (self.applianceid, self.version)).remove()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars.setdefault('publish-content', set()).add(self.vmdir)
