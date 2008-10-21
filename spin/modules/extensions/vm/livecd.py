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

from spin.event   import Event

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
      requires = ['kickstart-file', 'pkglist', 'repodata-directory']
    )

    self.baseimg  = self.mddir / 'ext3fs.img'
    self.builddir = self.mddir / 'build'
    self.tmpdir   = self.mddir / 'tmp'
    self.livecd   = self.mddir / '%s-livecd.iso' % self.applianceid

    self.DATA =  {
      'config': ['.'],
      'input':  [self.baseimg],
      'output': [self.livecd, self.baseimg],
      'variables': ['cvars[\'pkglist\']'],
    }

    self.creator = None
    self.ks = None
    self._scripts = []

  def setup(self):
    self.diff.setup(self.DATA)

    # read supplied kickstart
    self.ks = self.read_kickstart()

    self._update_ks_repos(self.ks)
    self._prep_ks_scripts(self.ks)

    # create image creator
    self.creator = SpinLiveImageCreator(self, self.ks,
                                        '%s-livecd' % self.applianceid)
    self.creator.skip_compression = not self.config.getbool('@compress', True)
    self.creator.skip_minimize    = not self.config.getbool('@minimize', True)

  def run(self):
    ## todos
    ## shell command outputs - too verbose for standard run
    ## hook up logging to spin, either by modifying spin or modyfing imgcreate

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


class SpinLiveImageCreator(vms.SpinImageCreatorMixin,
                           imgcreate.LiveImageCreator):
  def __init__(self, event, *args, **kwargs):
    imgcreate.LiveImageCreator.__init__(self, *args, **kwargs)
    vms.SpinImageCreatorMixin.__init__(self, event)

  def _base_on(self, base_on):
    if pps.path(base_on).exists():
      pps.path(base_on).cp(self._image, link=True, force=True)

  def _cleanup(self):
    if self._image and pps.path(self._image).exists():
      pps.path(self._image).rename(self.event.baseimg)

  def package(self, destdir = "."):
    # also copy image elsewhere for faster base_on'ing
    pps.path(self._image).cp(self.event.baseimg, link=True, force=True)
    imgcreate.LiveImageCreator.package(self, destdir=destdir)
