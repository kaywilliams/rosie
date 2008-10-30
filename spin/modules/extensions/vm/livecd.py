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
livecd.py

Creates a livecd image (.iso)
"""

import imgcreate

from rendition import pps

from spin.errors import SpinError
from spin.event  import Event

from spin.modules.shared import vms

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['LivecdEvent'],
  description = 'creates an appliance livecd',
  group       = 'vm',
)

class LivecdEvent(vms.VmCreateMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'livecd',
      parentid = 'vm',
      requires = ['kickstart', 'pkglist-install-packages']
    )

    self.baseimg  = self.mddir / 'ext3fs.img'
    self.builddir = self.mddir / 'build'
    self.tmpdir   = self.mddir / 'tmp'
    self.livecd   = self.mddir / '%s-livecd.iso' % self.applianceid

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [self.livecd, self.baseimg],
      'variables': ['cvars[\'pkglist-install-packages\']'],
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
    self.creator = SpinLiveImageCreator(self, self.ks,
                                        '%s-livecd' % self.applianceid)
    self.creator.skip_compression = not self.config.getbool('@compress', True)
    self.creator.skip_minimize    = not self.config.getbool('@minimize', True)

  def run(self):
    ## todos
    ## shell command outputs - too verbose for standard run
    ## hook up logging to spin, either by modifying spin or modyfing imgcreate

    # if scripts change, remove base
    if not self._check_ks_scripts():
      self.baseimg.rm(force=True)

    try:
      self.creator.mount(base_on=self.baseimg,
                         cachedir=self.builddir)
      self.creator.install()
      self.creator.configure()
      self.creator.unmount()
      self.creator.package(self.mddir)
    finally:
      self.creator.cleanup()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars.setdefault('publish-content', set()).add(self.livecd)

    self.creator = None


class SpinLiveImageCreator(vms.SpinImageCreatorMixin,
                           imgcreate.LiveImageCreator):
  def __init__(self, event, *args, **kwargs):
    imgcreate.LiveImageCreator.__init__(self, *args, **kwargs)
    vms.SpinImageCreatorMixin.__init__(self, event)

  def _base_on(self, base_on):
    if pps.path(base_on).exists():
      pps.path(base_on).cp(self._image, link=True, force=True)
      vms.SpinImageCreatorMixin._base_on(self, base_on)

  def _cleanup(self):
    if self._image and pps.path(self._image).exists():
      pps.path(self._image).rename(self.event.baseimg)

  def _check_required_packages(self):
    if 'syslinux' not in self._get_pkglist_names():
      raise SyslinuxRequiredError()

  def package(self, destdir = '.'):
    # also copy image elsewhere for faster base_on'ing
    pps.path(self._image).cp(self.event.baseimg, link=True, force=True)
    imgcreate.LiveImageCreator.package(self, destdir=destdir)

class SyslinuxRequiredError(SpinError):
  message = ( "Creating an appliance livecd requires that the 'syslinux' "
              "package be included in the appliance." )
