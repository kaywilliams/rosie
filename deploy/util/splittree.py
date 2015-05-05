#
# Copyright (c) 2015
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
import copy
import os
import re
import rpm

from math import ceil

from deploy.util import FormattedFile as ffile
from deploy.util import pkgorder
from deploy.util import rxml
from deploy.util import si

from deploy.util import sync

from deploy.util.pps.Path.error import PathError

from deploy.constants import RPM_GLOB, SRPM_GLOB

TS = rpm.TransactionSet()
TS.setVSFlags(-1)

SIZE_ALIASES = {
  'CD':  '640MB',
  'DVD': '4.7GB'
}

def parse_size(s):
  s = s.upper()
  if s in SIZE_ALIASES: s = SIZE_ALIASES[s]
  return si.parse(s)


class Timber:
  "Split trees like no other"
  def __init__(self, discsize='640MB', dosrc=False):
    self.discsize = parse_size(discsize)
    if self.discsize < si.parse('100MiB'):
      raise ValueError, "Minimum disc size for iso generation is 100 MiB"
    self.discsize = ( 99 * self.discsize ) / 100 # allow for file size rounding
    self.dosrc = dosrc
    self.name = None
    self.pkgorder = None

    # the following must be pps.Path objects
    self.u_tree = None     # unified tree
    self.u_src_tree = None # unifed source tree
    self.s_tree = None     # split tree

    self.product_path = None # path to rpms, relative to u_tree

    self.rpm_disc_map = None
    self.srpm_disc_map = None

    self.reverse_srpms = False

    self.discinfo_vars = None
    self.common_files = [] #!
    self.difmt = None

  def create_discinfo(self, discnumber):
    "Create a .discinfo file for disc number in split tree"
    if isinstance(self.difmt, dict):
      discinfo = ffile.DictToFormattedFile(self.difmt)
    elif isinstance(self.difmt, rxml.tree.XmlTreeElement):
      discinfo = ffile.XmlToFormattedFile(self.difmt)
    else:
      raise ValueError, "Unsupported format %s for pkgorder.difmt" % type(self.difmt)

    if self.discinfo_vars is None:
      difile = self.u_tree/'.discinfo'
      if not difile.exists():
        raise RuntimeError, "Error: .discinfo doesn't exist in unified tree"
      self.discinfo_vars = discinfo.read(difile)
    vars = copy.copy(self.discinfo_vars)
    vars['discs'] = str(discnumber)
    discinfo.write(
      self.s_tree/'%s-disc%d' % (self.name, discnumber)/'.discinfo',
      **vars
    )

  def cleanup(self):
    self.s_tree.glob('%s-disc*' % self.name).rm(recursive=True, force=True)

  def compute_layout(self):
    srpm_nregex = '(?i).*\.src\.rpm'

    # rpms
    totalsize = self.u_tree.findpaths(nregex=srpm_nregex).getsize()
    rpmsize = self.u_tree.findpaths(glob=RPM_GLOB, nregex=srpm_nregex).getsize()

    extrasize = totalsize - rpmsize

    ndiscs = int(ceil(float(totalsize)/self.discsize))
    nrpmdiscs = self.__consume_discs(rpmsize + extrasize)
    self.rpm_disc_map = range(1, nrpmdiscs + 1)

    # srpms
    nsrpmdiscs = 0
    if self.dosrc:
      srpmsize = self.u_src_tree.findpaths(glob=SRPM_GLOB).getsize()
      ndiscs = int(ceil(float(srpmsize)/self.discsize))
      nsrpmdiscs = self.__consume_discs(srpmsize)
      self.srpm_disc_map = range(nrpmdiscs + 1, nrpmdiscs + nsrpmdiscs + 1)

    self.numdiscs = nrpmdiscs + nsrpmdiscs

  def __consume_discs(self, size):
    i_size = 0
    num_discs = 0
    while i_size < size:
      num_discs += 1
      i_size += self.discsize
    return num_discs

  def split_trees(self):
    "Split stuff up"
    for i in self.rpm_disc_map:
      discpath = self.s_tree/'%s-disc%d' % (self.name, i)
      discpath.mkdirs()
      if i == 1: # put release files on disc 1
        for file in self.u_tree.findpaths(
            nregex='.*/(\.discinfo|.+\.[Rr][Pp][Mm]|(S)?RPMS|%s)$' % self.product_path,
            mindepth=1, maxdepth=1):
          sync.sync(file, discpath, link=True)
      else:
        for file in self.common_files:
          sync.sync(file, discpath, link=True)
      self.create_discinfo(i)

    if self.dosrc:
      for i in self.srpm_disc_map:
        discpath = self.s_tree/'%s-disc%d' % (self.name, i)
        (discpath/'SRPMS').mkdirs()
        for file in self.common_files:
          sync.sync(file, discpath, link=True)
        self.create_discinfo(i)

  def split_rpms(self):
    packages = {}
    pkgdir = self.u_tree/self.product_path

    for rpm in pkgdir.findpaths(glob='*.[Rr][Pp][Mm]'):
      packages.setdefault(nvra(rpm), []).append(rpm)

    order = [ pkgtup_to_nvra(x) for x in
              pkgorder.parse_pkgorder(self.pkgorder) ]

    disc = self.rpm_disc_map[0]
    discpath = self.s_tree/'%s-disc%d' % (self.name, disc)

    (discpath/self.product_path).mkdirs()

    used = discpath.du(bytes=True)
    for rpmnvra in order:
      if not packages.has_key(rpmnvra): continue

      newsize = used

      for file in packages[rpmnvra]:
        if (discpath/self.product_path/file.basename).exists(): continue

        newsize = used + file.getsize()

        if newsize > self.discsize:
          # move to the next disc
          try:
            nextdisc = self.rpm_disc_map.index(disc+1)
            disc     = self.rpm_disc_map[nextdisc]
            discpath = self.s_tree/'%s-disc%d' % (self.name, disc)
            (discpath/self.product_path).mkdirs()
            used = discpath.du(bytes=True)
            sync.sync(file, discpath/self.product_path, link=True)
            newsize = used + file.getsize()
          except (IndexError, ValueError):
            disc = disc - 1
            print 'DEBUG: overflow from disc %d onto disc %d' % (disc+1, disc)
            print 'DEBUG: newsize: %d maxsize: %d' % (newsize, maxsize)
            raise
        else:
          sync.sync(file, discpath/self.product_path, link=True)
      used = newsize

  def split_srpms(self):
    if not self.dosrc:
      return

    srpms = self.u_src_tree.findpaths(glob='*.[Ss][Rr][Cc].[Rr][Pp][Mm]')

    srpms.sort('size')

    # keep list of SRPM trees and their sizes
    sizes = []
    for disc in self.srpm_disc_map:
      sizes.append(
        [ (self.s_tree/'%s-disc%d' % (self.name, disc)).findpaths().getsize(),
          disc ]
      )
      (self.s_tree/'%s-disc-%d/SRPMS' % (self.name, disc)).mkdirs()
    sizes.sort()

    # add srpm to the smallest source tree
    for srpm in srpms:
      sync.sync(srpm, self.s_tree/'%s-disc%d/SRPMS' % (self.name, sizes[0][1]),
                link=True)
      sizes[0][0] += srpm.getsize()
      sizes.sort()


def nvra(pkgfile):
  fd = os.open(pkgfile, os.O_RDONLY)
  h = TS.hdrFromFdno(fd)
  os.close(fd)
  return '%s-%s-%s.%s' % (h['name'], h['version'], h['release'], h['arch'])

def pkgtup_to_nvra(pkgtup):
  return '%s-%s-%s.%s' % (pkgtup[0], pkgtup[3], pkgtup[4], pkgtup[1])
