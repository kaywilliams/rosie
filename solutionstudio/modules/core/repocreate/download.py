#
# Copyright (c) 2010
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

from rendition.repo import RPM_PNVRA_REGEX

from systembuilder.errors    import SystemBuilderError
from systembuilder.event     import Event
from systembuilder.logging   import L1, L2

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['DownloadEvent'],
  description = 'downloads pkglist RPMs',
  group       = 'repocreate',
)

class DownloadEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'download',
      parentid = 'repocreate',
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

    rpmset = set()
    for pkg in self.cvars['pkglist']:
      rpmset.add('%s.rpm' % pkg)

    processed_rpmset = set()
    for repo in self.cvars['repos'].values():
      now = time.time()
      for rpminfo in repo.repocontent.filter():
        rpm = repo.url//rpminfo['file']
        _,_,_,_,a = self._deformat(rpm)
        if ( rpm.basename in rpmset and
             rpm.basename not in processed_rpmset and
             a in self._validarchs ):
          rpm.stat(populate=False).update(
            st_size  = rpminfo['size'],
            st_mtime = rpminfo['mtime'],
            st_mode  = (stat.S_IFREG | 0644),
            st_atime = now)
          processed_rpmset.add(rpm.basename)
          self.io.add_fpath(rpm, self.builddata_dest, id=repo.id)
          self.cvars['rpms-by-repoid'].setdefault(repo.id, []).append(
            self.builddata_dest // rpm.basename)
      if repo.id in self.cvars['rpms-by-repoid']:
        self.cvars['rpms-by-repoid'][repo.id].sort()

    if rpmset != processed_rpmset:
      raise RpmsNotFoundError(sorted(rpmset - processed_rpmset))

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


class RpmsNotFoundError(SystemBuilderError):
  message = "The following RPMs were not found in any input repos:\n%(rpms)s"
