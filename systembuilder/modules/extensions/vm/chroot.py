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

Creates a chroot based off of the distribution
"""

import subprocess

import imgcreate

from rendition import pps

from systembuilder.event   import Event
from systembuilder.logging import L1, L2, L3

from systembuilder.modules.shared import vms

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ChrootEvent'],
  description = 'creates a chroot installation of the distribution',
  group       = 'vm',
)

class ChrootEvent(vms.VmCreateMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'chroot',
      parentid = 'vm',
      requires = ['local-baseurl-kickstart', 'pkglist-install-packages'],
      conditionally_comes_before = ['publish'],
    )

    self.builddir = self.mddir / 'build'
    self.tmpdir   = self.mddir / 'tmp'
    self.chroot   = self.mddir / self.distributionid
    self.chrootgz = self.mddir / self.distributionid+'.tar.gz'

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

    if self.cvars['local-baseurl-kickstart'] is None:
      raise vms.KickstartRequiredError(modid=self.id)

    # read supplied kickstart
    self.ks = self.cvars['local-baseurl-kickstart']
    self.DATA['input'].append(self.cvars['local-baseurl-kickstart-file'])

    self._prep_ks_scripts()

    # create image creator
    self.creator = SystemBuilderRawImageCreator(self,
                     compress = self.config.getbool('@compress', 'True'),
                     ks       = self.ks,
                     name     = self.distributionid)

  def run(self):
    ## todos
    ## shell command outputs - too verbose for standard run
    ## hook up logging to systembuilder, either by modifying systembuilder or modyfing imgcreate

    # if scripts change, remove base
    if not self._check_ks_scripts():
      (self.chroot).rm(recursive=True, force=True)
      (self.chrootgz).rm(force=True)

    try:
      self.log(3, L1("mounting chroot"))
      self.creator.mount(base_on=self.chroot,
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

    self.creator = None

class SystemBuilderRawImageCreator(vms.SystemBuilderImageCreatorMixin,
                          imgcreate.ImageCreator):
  def __init__(self, event, compress=True, *args, **kwargs):
    imgcreate.ImageCreator.__init__(self, *args, **kwargs)
    vms.SystemBuilderImageCreatorMixin.__init__(self, event)

    self.compress = compress

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
    base_on_tgz = base_on+'.tar.gz'

    if base_on_tgz.exists():
      self.event.logger.log(2, L1("extracting previous chroot"))
      cmd = ['tar', '--extract', '--gzip', '--preserve-permissions',
                    '--atime-preserve', '--xattrs',
                    '--file', base_on_tgz,
                    '--directory', self._instroot]
      if self.event.logger.test(5):
        cmd.append('--verbose')
      subprocess.call(cmd)
      vms.SystemBuilderImageCreatorMixin._base_on(self, base_on_tgz)

    elif base_on.exists():
      self.event.logger.log(2, L1("verifying previous chroot"))
      # check to see if it looks like we have a chroot there
      dirs = ['bin', 'dev', 'etc', 'lib', 'proc', 'root',
              'sbin', 'sys', 'usr', 'var']
      base_ok = True
      for dir in dirs:
        base_ok = base_ok and (base_on/dir).exists()

      if base_ok:
        base_on.rename(self._instroot)
        vms.SystemBuilderImageCreatorMixin._base_on(self, base_on)

  def _cleanup(self):
    if self._instroot and pps.path(self._instroot).exists():
      (self.event.chroot).rm(recursive=True, force=True)
      pps.path(self._instroot).rename(self.event.chroot)

    self.event.builddir.rm(recursive=True, force=True)

  def package(self, destdir = '.'):
    # basically the same as the original package method, but slightly more
    # robust (less sensitive to whether destdir exists or not)

    self._stage_final_image()

    if self.compress:
      dst = destdir/self.event.chrootgz.basename
      dst.rm(force=True)
      (self._outdir/dst.basename).rename(dst)

    else:
      dst = destdir/self.event.chroot.basename
      dst.rm(recursive=True, force=True)
      chroot = pps.path(self._outdir).listdir()
      assert len(chroot) == 1
      chroot[0].rename(dst)

  def _stage_final_image(self):
    if self.compress:
      self.event.logger.log(2, L1("compressing chroot"))
      cmd = ['tar', '--create', '--gzip', '--xattrs',
             '--file', pps.path(self._outdir)/self.event.chrootgz.basename,
             '--directory', self._instroot]
      if self.event.logger.test(5): cmd.append('--verbose')
      cmd.extend([ x.basename for x in pps.path(self._instroot).listdir() ])

      self.event.logger.log(4, L3(' '.join(cmd)))
      subprocess.call(cmd)

      pps.path(self._instroot).rm(recursive=True, force=True)
    else:
      imgcreate.ImageCreator._stage_final_image(self)
