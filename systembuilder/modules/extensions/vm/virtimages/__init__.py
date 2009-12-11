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
virtimages

Create virtual machine images of various types
"""

import appcreate
import imgcreate

from rendition import pps
from rendition import rxml

from spin.errors  import SpinError
from spin.event   import Event
from spin.logging import L1

from spin.modules.shared import vms

from libvirt import LibVirtEvent
from vmware  import VmwareEvent

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['VirtimageBaseEvent', 'LibVirtEvent', 'VmwareEvent'],
  description = 'creates virtual machine images of various types',
  group       = 'vm',
)


class VirtimageBaseEvent(vms.VmCreateMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'virtimage-base',
      parentid = 'vm',
      requires = ['local-baseurl-kickstart', 'pkglist'],
      provides = ['virtimage-disks', 'virtimage-xml'],
    )

    self.builddir = self.mddir / 'build'
    self.tmpdir   = self.mddir / 'tmp'
    self.outdir   = self.mddir / self.distributionid

    self.DATA =  {
      #'config': ['.'], # don't track this for now
      'input':  [],
      'output': [],
      'variables': ['cvars[\'pkglist-install-packages\']'],
    }

    self.creator = None
    self.ks = None
    self._scripts = []

  def setup(self):
    self.diff.setup(self.DATA)
    self.outdir.mkdirs()

    if self.cvars['local-baseurl-kickstart'] is None:
      raise vms.KickstartRequiredError(modid=self.id)

    # read supplied kickstart
    self.ks = self.cvars['local-baseurl-kickstart']
    self.DATA['input'].append(self.cvars['local-baseurl-kickstart-file'])

    # add outputs
    for part in self.ks.handler.partition.partitions:
      self.DATA['output'].append(
        self.outdir/'%s-%s.raw' % (self.distributionid, part.disk))
    self.DATA['output'].append(self.outdir/'%s.xml' % self.distributionid)

    self._prep_ks_scripts()

    # create image creator
    self.creator = SpinDistributionImageCreator(self,
                     self.ks,
                     name        = self.distributionid,
                     disk_format = 'raw',
                     vmem        = int(self.config.get('@vmem', '512')),
                     vcpu        = int(self.config.get('@vcpu', '1')))

  def run(self):

    # if scripts or partitions change, remove base
    if ( not self._check_ks_scripts() or
         not self._check_partitions() ):
      self.outdir.listdir('*.raw').rm(force=True)

    # prepare base_on
    base_on = {}
    for part in self.ks.handler.partition.partitions:
      if not (self.outdir/'%s-%s.raw' % (self.distributionid, part.disk)).exists():
        # if any disk doesn't exist for a partition, give up and start over
        self.outdir.listdir('*.raw').rm(force=True)
        base_on = None
        break
      else:
        base_on[self.outdir/'%s-%s.raw' % (self.distributionid, part.disk)] = part.disk

    try:
      self.log(3, L1("mounting disks"))
      self.creator.mount(base_on=base_on, cachedir=self.builddir)
      self.log(3, L1("installing selected packages"))
      self.creator.install()
      self.log(3, L1("configuring virtual machine"))
      self.creator.configure()
      self.log(3, L1("unmounting disks"))
      self.creator.unmount()
      self.log(3, L1("packacking virtual machine"))
      self.creator.package(self.mddir, package="none", include=None)
    finally:
      self.creator.cleanup()

    # modify config for conversion - requries /image/name/@version and
    # /image/description/text()
    conf = self.outdir/'%s.xml' % self.distributionid
    vxml = rxml.tree.read(conf)
    vxml.get('name').attrib['version'] = self.version
    rxml.tree.Element('description', text=self.fullname, parent=vxml)
    vxml.write(conf)

  def apply(self):
    self.io.clean_eventcache()

    self.cvars.setdefault('virtimage-disks', [])

    for part in self.ks.handler.partition.partitions:
      self.cvars['virtimage-disks'].append(
        self.outdir/'%s-%s.raw' % (self.distributionid, part.disk))
    self.cvars['virtimage-xml'] = self.outdir/'%s.xml' % self.distributionid


class SpinDistributionImageCreator(vms.SpinImageCreatorMixin,
                                appcreate.DistributionImageCreator):
  def __init__(self, event, *args, **kwargs):
    appcreate.DistributionImageCreator.__init__(self, *args, **kwargs)
    vms.SpinImageCreatorMixin.__init__(self, event)

  def _check_required_packages(self):
    if 'grub' not in self._get_pkglist_names():
      raise GrubRequiredError()

  def _mount_instroot(self, base_on = None):

    # base_on should be a pps filename: diskname pair
    if base_on is not None:
      # TODO - this could be refactored with existing _mount_instroot, prolly
      self._setattr_('__imgdir', self._mkdtemp())

      # create disks
      for id, name in base_on.items():
        # move old base(s) into place
        if id.exists():
          id.cp(self._getattr_('__imgdir'), link=True, force=True)

        disk = appcreate.SparseLoopbackDisk(
                '%s/%s' % (self._getattr_('__imgdir'), id.basename),
                id.stat().st_size)
        self._getattr_('__disks')[name] = disk

      self._setattr_('__instloop', SpinPartitionedMount( #!
                                     self._getattr_('__disks'),
                                     self._instroot))

      for part in self.ks.handler.partition.partitions:
        self._getattr_('__instloop').add_partition(
          int(part.size), part.disk, part.mountpoint, part.fstype)

      try:
        self._getattr_('__instloop').mount(format=False)
      except appcreate.MountError, e:
        raise imgcreate.CreatorError("Failed mount disks: %s" % e)

      vms.SpinImageCreatorMixin._base_on(self, base_on)

    else:
      appcreate.DistributionImageCreator._mount_instroot(self)

  def _cleanup(self):
    try:
      for file in pps.path(self._getattr_('__imgdir')).listdir():
        file.cp(self.mddir, link=True, force=True)
    except:
      pass

class GrubRequiredError(SpinError):
  message = ( "Creating an distribution virtual image requires that the 'grub' "
              "package be included in the distribution." )

import inspect
import logging
import subprocess

# the following classes use the same 'Xtreem Kool Hak' as
# SpinImageCreatorMixin for _getattr_ (see shared/vms.py for details)
#
# These classes allow appcreator to use base_on for its images - specifically,
# the disk images are not automatically formatted upon creation
#
# Most of the method code here is unchanged from the original; lines with
# differences end in '#!'

class SpinExtDiskMount(imgcreate.ExtDiskMount):
  def _getattr_(self, attr):
    for cls in inspect.getmro(self.__class__):
      if cls == SpinExtDiskMount: continue # don't loop infinitely
      atn = '_%s%s' % (cls.__name__, attr)
      if hasattr(self, atn):
        return getattr(self, atn)
    else:
      raise AttributeError(attr)

  def __create(self, format=True): #!
    # only formats if format is True, otherwise passes #!
    resize = False
    if not self.disk.fixed() and self.disk.exists():
      resize = True

    self.disk.create()

    if resize:
      self._getattr_('__resize_filesystem')()
    else:
      if format: self._getattr_('__format_filesystem')() #!

  def mount(self, format=True): #!
    self.__create(format=format) #!
    imgcreate.DiskMount.mount(self)

class SpinPartitionedMount(appcreate.PartitionedMount):
  def _getattr_(self, attr):
    for cls in inspect.getmro(self.__class__):
      if cls == SpinPartitionedMount: continue # don't loop infinitely
      atn = '_%s%s' % (cls.__name__, attr)
      if hasattr(self, atn):
        return getattr(self, atn)
    else:
      raise AttributeError(attr)

  def __format_disks(self, format=True): #!
    # only formats if format is True, otherwise identical #!
    if format: #!
      logging.debug("Formatting disks")
      for dev in self.disks.keys():
        d = self.disks[dev]
        logging.debug("Initializing partition table for %s" % (d['disk'].device))
        rc = subprocess.call(["/sbin/parted", "-s", d['disk'].device, "mklabel", "msdos"]) 
        if rc != 0:
          raise appcreate.MountError("Error writing partition table on %s" % d['disk'].device)

    logging.debug("Assigning partitions to disks")
    for n in range(len(self.partitions)):
      p = self.partitions[n]

      if not self.disks.has_key(p['disk']):
        raise appcreate.MountError("No disk %s for partition %s" % (p['disk'], p['mountpoint']))

      d = self.disks[p['disk']]
      d['numpart'] += 1
      if d['numpart'] > 3:
        # Increase allocation of extended partition to hold this partition
        d['extended'] += p['size']
        p['type'] = 'logical'
        p['num'] = d['numpart'] + 1
      else:
        p['type'] = 'primary'
        p['num'] = d['numpart']

      p['start'] = d['offset']
      d['offset'] += p['size']
      d['partitions'].append(n)
      logging.debug("Assigned %s to %s%d at %d at size %d" % (p['mountpoint'], p['disk'], p['num'], p['start'], p['size']))

    # XXX we should probably work in cylinder units to keep fdisk happier..
    if format: #!
      start = 0
      logging.debug("Creating partitions")
      for p in self.partitions:
        d = self.disks[p['disk']]
        if p['num'] == 5:
          logging.debug("Added extended part at %d of size %d" % (p['start'], d['extended']))
          rc = subprocess.call(["/sbin/parted", "-s", d['disk'].device, "mkpart", "extended",
                                "%dM" % p['start'], "%dM" % (p['start'] + d['extended'])])

        logging.debug("Add %s part at %d of size %d" % (p['type'], p['start'], p['size']))
        rc = subprocess.call(["/sbin/parted", "-s", d['disk'].device, "mkpart",
                              p['type'], "%dM" % p['start'], "%dM" % (p['start']+p['size'])])

        # XXX disabled return code check because parted always fails to
        # reload part table with loop devices. Annoying because we can't
        # distinguish this failure from real partition failures :-(
        if rc != 0 and 1 == 0:
          raise appcreate.MountError("Error creating partition on %s" % d['disk'].device)

  def mount(self, format=True): #!
    # only formats if format is True; creates custom classes of mount/disks #!
    # otherwise identical #!
    for dev in self.disks.keys():
      d = self.disks[dev]
      d['disk'].create()

    self.__format_disks(format=format) #!
    self._getattr_('__map_partitions')()
    self._getattr_('__calculate_mountorder')()

    for mp in self.mountOrder:
      p = None
      for p1 in self.partitions:
        if p1['mountpoint'] == mp:
          p = p1
          break

      if mp == 'swap':
        subprocess.call(["/sbin/mkswap", p['device']])
        continue

      rmmountdir = False
      if p['mountpoint'] == "/":
        rmmountdir = True
      pdisk = SpinExtDiskMount( #!
                imgcreate.RawDisk(p['size'] * 1024 * 1024, p['device']),
                self.mountdir + p['mountpoint'],
                p['fstype'],
                4096,
                p['mountpoint'],
                rmmountdir)
      pdisk.mount(format=format) #!
      p['mount'] = pdisk
