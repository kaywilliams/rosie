#
# Copyright (c) 2013
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
import stat 
import time

from rpmUtils.arch import getArchList

from deploy.errors    import DeployEventError 
from deploy.event     import Event
from deploy.main      import ARCH_MAP 

from deploy.modules.shared import ShelveMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['DownloadEvent'],
    description = 'downloads package list RPMs',
    group       = 'repocreate',
  )

class DownloadEvent(ShelveMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'download',
      version = 1.01,
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['rpmsdir', 'rpms'],
      requires = ['pkglist', 'repos'],
      conditionally_requires = ['groupfile'],
    )

    self._validarchs = getArchList(ARCH_MAP[self.arch])

    self.DATA = {
      'variables': ['packagepath', 'cvars[\'pkglist\']'],
      'input':     [],
      'output':    [],
    }

    ShelveMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    self.rpmsdir = self.mddir//self.packagepath
    self.DATA['variables'].append('rpmsdir')

    # setup for downloads
    for repo in self.cvars['repos'].values():
      if self.type != 'system' and repo.download is False:
        continue
      for subrepo in repo.subrepos.values():
        now = time.time()
        # populate rpm time and size from repodata values (for performance)
        if subrepo.id not in self.cvars['pkglist']:
          continue
        for tup in self.cvars['pkglist'][subrepo.id]: 
          _, _, path, size, mtime = tup
          rpm = subrepo.url//path
          rpm.stat(populate=False).update(
            st_size  = size,
            st_mtime = mtime,
            st_mode  = (stat.S_IFREG | 0644),
            st_atime = now)
          # add rpm for io sync
          self.io.add_fpath(rpm, self.rpmsdir, id=subrepo.id)

  def run(self):
    self.rpms = {}
    for subrepo in self.cvars['pkglist']:
      self.io.process_files(link=True, cache=True, what=subrepo, 
                            text=("downloading packages - '%s'" % subrepo))
      for f in self.io.list_output(what=subrepo):
        self.rpms[f] = subrepo
    self.shelve('rpms', self.rpms)

  def apply(self):
    self.cvars['rpmsdir'] = self.rpmsdir
    self.cvars['rpms'] = self.unshelve('rpms', {}) 

  def error(self, e):
    # performing a subset of Event.error since sync handles partially 
    # downloaded files
    if self.mdfile.exists():
      debugdir=(self.mddir + '.debug')
      debugdir.mkdir()
      self.mdfile.rename(debugdir / self.mdfile.basename)
   

#------ ERRORS ------#
class RpmsNotFoundError(DeployEventError):
  message = "The following RPMs were not found in any input repos:\n%(rpms)s"