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
import stat
import time

from rpmUtils.arch import getArchList

from spin.constants import RPM_PNVRA_REGEX
from spin.event     import Event
from spin.logging   import L1, L2

API_VERSION = 5.0
EVENTS = ['DownloadEvent']

class DownloadEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'download',
      parentid = 'software',
      provides = ['cached-rpms', 'rpms-by-repoid'],
      requires = ['pkglist', 'repos'],
    )

    self._validarchs = getArchList(self.arch)

    self.DATA = {
      'variables': ['cvars[\'pkglist\']'],
      'input':     [],
      'output':    [],
    }

    self.builddata_dest = self.mddir/'rpms'

  def setup(self):
    self.diff.setup(self.DATA)

    self.cvars['rpms-by-repoid'] = {}
    processed = []

    for repo in self.cvars['repos'].values():
      rpms = {}
      now = time.time()
      for rpminfo in repo.repocontent:
        rpm = repo.url//rpminfo['file']
        _,n,v,r,a = self._deformat(rpm)
        nvra = '%s-%s-%s.%s' % (n,v,r,a)
        if nvra in self.cvars['pkglist'] and nvra not in processed and \
             a in self._validarchs:
          rpm.stat(populate=False).update(
            st_size  = rpminfo['size'],
            st_mtime = rpminfo['mtime'],
            st_mode  = (stat.S_IFREG | 0644),
            st_atime = now)
          rpms[rpm.basename] = rpm
          processed.append(nvra)

      self.io.add_fpaths(rpms.values(), self.builddata_dest, id=repo.id)
      if rpms:
        self.cvars['rpms-by-repoid'][repo.id] = \
          sorted([self.builddata_dest//rpm for rpm in rpms.keys()])

  def run(self):
    for repo in self.cvars['repos'].values():
      self.io.sync_input(link=True, cache=True, what=repo.id,
                         text=("downloading packages - '%s'" % repo.id))

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['cached-rpms'] = self.io.list_output()

  def _deformat(self, rpm):
    """
    p[ath],n[ame],v[ersion],r[elease],a[rch] = _deformat(rpm)

    Takes an rpm with an optional path prefix and splits it into its component parts.
    Returns a path, name, version, release, arch tuple.
    """
    try:
      return RPM_PNVRA_REGEX.match(rpm).groups()
    except (AttributeError, IndexError), e:
      self.log(2, L2("DEBUG: Unable to extract rpm information from name '%s'" % rpm))
      return (None, None, None, None, None)

  def error(self, e):
    # performing a subset of Event.error since sync handles partially downloaded files
    if self.mdfile.exists():
      debugdir=(self.mddir + '.debug')
      debugdir.mkdir()
      self.mdfile.rename(debugdir / self.mdfile.basename)
