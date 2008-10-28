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
virtimage.py

Creates a virtimage (xen, virsh) disk image.
"""

import appcreate
import imgcreate

from spin.errors import SpinError
from spin.event  import Event

from spin.modules.shared import vms

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['LibvirtVMEvent'],
  description = 'creates a libvirt (xen, virsh) virtual machine image',
  group       = 'vm',
)


class LibvirtVMEvent(vms.VmCreateMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'virtimage',
      parentid = 'vm',
      requires = ['kickstart', 'pkglist'],
      provides = ['publish-content']
    )

    self.vmdir    = self.mddir / 'vms'
    self.builddir = self.mddir / 'build'
    self.tmpdir   = self.mddir / 'tmp'
    self.app      = self.mddir / '%s.img' % self.applianceid

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [self.vmdir], #!
      'variables': ['cvars[\'pkglist\']'],
    }

    self.creator = None
    self.ks = None
    self._scripts = []

  def setup(self):
    self.diff.setup(self.DATA)

    if self.cvars['kickstart'] is None:
      raise vms.KickstartRequiredError(modid=self.id)

    # read supplied kickstart
    self.ks = self.cvars['kickstart']
    self.DATA['input'].append(self.cvars['kickstart-file'])

    self._prep_ks_scripts()

    # create image creator
    self.vmdir.mkdirs()
    self.creator = SpinApplianceImageCreator(self,
                     self.ks,
                     name     = self.applianceid,
                     format   = 'raw',
                     package  = 'none',
                     vmem     = self.config.get('@vmem', '512'),
                     vcpu     = self.config.get('@vcpu', '1'),
                     checksum = False)

  def run(self):

    try:
      ##self.creator.mount(base_on=X, cachedir=self.buiddir)
      self.creator.mount(cachedir=self.builddir)
      self.creator.install()
      self.creator.configure()
      self.creator.unmount()
      self.creator.package(self.vmdir)
    finally:
      self.creator.cleanup()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars.setdefault('publish-content', set()).add(self.vmdir)


class SpinApplianceImageCreator(vms.SpinImageCreatorMixin,
                                appcreate.ApplianceImageCreator):
  def __init__(self, event, *args, **kwargs):
    appcreate.ApplianceImageCreator.__init__(self, *args, **kwargs)
    vms.SpinImageCreatorMixin.__init__(self, event)

  def _check_required_packages(self):
    if 'grub' not in self._get_pkglist_names():
      raise GrubRequiredError()

  def _cleanup(self):
    if self._instroot and pps.path(self._instroot).exists():
      self.event.vmdir.rm(recursive=True, force=True)
      pps.path(self._instroot).rename(self.event.vmdir)

class GrubRequiredError(SpinError):
  message = ( "Creating an appliance virtual image requires that the 'grub' "
              "package be included in the appliance." )
