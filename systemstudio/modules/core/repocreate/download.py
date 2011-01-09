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

from systemstudio.util.repo import RPM_PNVRA_REGEX

from systemstudio.errors    import SystemStudioError
from systemstudio.event     import Event
from systemstudio.logging   import L1, L2

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

    # get urls for each subrepo
    urldict = {}
    for repo in self.cvars['repos'].values():
      for subrepo in repo.subrepos.values():
        urldict[subrepo.id] = subrepo.url
    
    for subrepo in self.cvars['pkglist'].keys():
      now = time.time()
      # populate rpm time and size from repodata values (for performance)
      for tup in self.cvars['pkglist'][subrepo]:
        _, _, path, size, mtime = tup
        rpm = urldict[subrepo]//path
        rpm.stat(populate=False).update(
          st_size  = size,
          st_mtime = mtime,
          st_mode  = (stat.S_IFREG | 0644),
          st_atime = now)
        # add rpm for to io sync
        self.io.add_fpath(rpm, self.builddata_dest, id=subrepo)
        self.cvars['rpms-by-repoid'].setdefault(subrepo, []).append(
          self.builddata_dest // rpm.basename)
    if repo.id in self.cvars['rpms-by-repoid']:
      self.cvars['rpms-by-repoid'][repo.id].sort()

  def run(self):
    for subrepo in self.cvars['pkglist'].keys():
      self.io.sync_input(link=True, cache=True, what=subrepo,
                         text=("downloading packages - '%s'" % subrepo))

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['cached-rpms'] = self.io.list_output()

  def error(self, e):
    # performing a subset of Event.error since sync handles partially downloaded files
    if self.mdfile.exists():
      debugdir=(self.mddir + '.debug')
      debugdir.mkdir()
      self.mdfile.rename(debugdir / self.mdfile.basename)


class RpmsNotFoundError(SystemStudioError):
  message = "The following RPMs were not found in any input repos:\n%(rpms)s"
