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
import subprocess

import virtinst
import virtinst.UnWare

from rendition import pps
from rendition import rxml

from spin.constants import KERNELS
from spin.event     import Event
from spin.logging   import L1

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
      requires = ['virtimage-conf', 'virtimage-raw'],
    )

    self.builddir = self.mddir/'build'
    self._publish = [] # list of files to add to publish

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [],
      'variables': ['applianceid', 'version', 'fullname',
                    'cvars[\'virtimage-conf\']',
                    'cvars[\'virtimage-raw\']'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    # add the virtimage stuff to our inputs
    self.DATA['input'].append(self.cvars['virtimage-conf'])
    for disk in self.cvars['virtimage-raw']:
      self.DATA['input'].append(disk)

    self.builddir.mkdirs()

  def run(self):

    # delete previous output
    self.mddir.listdir('%s*' % self.applianceid).rm()

    # copy image
    for img in self.cvars['virtimage-raw']:
      img.cp(self.builddir, link=True)

    # copy and modify config so virt-pack doesn't error
    conf = self.builddir/self.cvars['virtimage-conf'].basename
    vxml = rxml.tree.read(self.cvars['virtimage-conf'])
    vxml.get('name').attrib['version'] = self.version
    rxml.tree.Element('description', text=self.fullname, parent=vxml)
    vxml.write(conf)

    # convert

    self.log(3, L1("creating VMX files"))
    image = virtinst.ImageParser.parse_file(conf)
    vmx = virtinst.UnWare.Image(image)
    vmx.make(image.base)

    if self.config.getbool('@compress', 'True'):
      tdir = self.builddir/self.applianceid
      tdir.mkdirs()
      for f in self.builddir.listdir().filter(tdir.basename):
        f.rename(tdir/f.basename)

      cmd = ['tar', '--create', '--gzip',
             '--file', self.mddir/'%s.tgz' % self.applianceid,
             '--directory', tdir.dirname]
      if self.logger.test(5): cmd.append('--verbose')
      cmd.append(tdir.basename)

      self.log(3, L1("packaging and compressing image"))
      subprocess.call(cmd)

      self._publish = [self.mddir/'%s.tgz' % self.applianceid]
    else:
      for f in self.builddir.listdir():
        f.rename(self.mddir/f.basename)
      self._publish = self.builddir.listdir()

  def apply(self):
    self.builddir.rm(recursive=True, force=True)
    ##self.io.clean_eventcache() # don't do this, it erases output

    self.cvars.setdefault('publish-content', set())
    for f in self._publish:
      self.cvars['publish-content'].add(f)
