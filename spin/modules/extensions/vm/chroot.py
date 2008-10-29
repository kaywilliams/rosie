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
chroot.py

Creates a chroot based off of the appliance
"""

import imgcreate

from rendition import pps

from spin.event   import Event
from spin.logging import L1, L2

from spin.modules.shared import vms

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ChrootEvent'],
  description = 'creates a chroot installation of the appliance',
  group       = 'vm',
)

class ChrootEvent(vms.VmCreateMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'chroot',
      parentid = 'vm',
      requires = ['kickstart-file', 'pkglist-install-packages', 'repodata-directory'],
      comes_before = ['publish'],
    )

    self.builddir = self.mddir / 'build'
    self.tmpdir   = self.mddir / 'tmp'
    self.vmdir    = self.mddir / 'raw'

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [],
      'variables': ['cvars[\'pkglist-install-packages\']'],
    }

    self.creator = None # the image creator instance
    self.ks = None      # the kickstart we're using
    self._scripts = []  # list of scripts and properties, for difftest

  def setup(self):
    self.diff.setup(self.DATA)

    # read supplied kickstart
    self.ks = self.read_kickstart()

    self._update_ks_repos(self.ks)
    self._prep_ks_scripts(self.ks)

    # create image creator
    self.creator = SpinRawImageCreator(self, self.ks, 'raw')

  def run(self):
    ## todos
    ## shell command outputs - too verbose for standard run
    ## hook up logging to spin, either by modifying spin or modyfing imgcreate

    self._check_ks_scripts() # remove base if ks scripts change

    try:
      self.log(3, L1("mounting chroot"))
      self.creator.mount(base_on=self.vmdir,
                         cachedir=self.builddir)
      self.log(3, L1("installing selected packages"))
      self.creator.install()
      self.log(3, L1("configuring chroot"))
      self.creator.configure()
      self.log(3, L1("unmounting chroot"))
      self.creator.unmount()
      self.log(3, L1("packaging chroot"))
      self.creator.package(self.mddir)
    finally:
      self.creator.cleanup()

  def apply(self):
    ##self.io.clean_eventcache() # don't do this, this deletes chroot
    self.tmpdir.rm(recursive=True, force=True)


class SpinRawImageCreator(vms.SpinImageCreatorMixin,
                          imgcreate.ImageCreator):
  def __init__(self, event, *args, **kwargs):
    imgcreate.ImageCreator.__init__(self, *args, **kwargs)
    vms.SpinImageCreatorMixin.__init__(self, event)

  def _get_fstab(self):
    # livecd's version doesn't work out of the box because it asks for
    # a filesystem type which doesn't exist on raw disk images
    # returning empty instead; doesn't seem to matter
    return ""

  def _mount_instroot(self, base_on = None):
    if base_on:
      self._base_on(base_on)

  def _base_on(self, base_on):
    base_on = pps.path(base_on)
    # check to see if it looks like we have a chroot there
    dirs = ['bin', 'dev', 'etc', 'lib', 'proc', 'root',
            'sbin', 'sys', 'usr', 'var']
    base_ok = True
    for dir in dirs:
      base_ok = base_ok and (base_on/dir).exists()

    if base_ok:
      base_on.rename(self._instroot)
      vms.SpinImageCreatorMixin._base_on(self, base_on)

  def _cleanup(self):
    if self._instroot and pps.path(self._instroot).exists():
      pps.path(self._instroot).rename(self.event.vmdir)
