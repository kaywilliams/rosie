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

import re

from rendition import pps

from spin.logging   import L1, L2
from spin.constants import BOOLEANS_FALSE

from rendition.repo      import ReposFromXml, ReposFromFile, getDefaultRepos
from rendition.repo.repo import YumRepo, RepoContainer

__all__ = ['RepoEventMixin', 'SpinRepo']


class SpinRepo(YumRepo):
  def __init__(self, **kwargs):
    YumRepo.__init__(self, **kwargs)
    self.localurl = None

  @property
  def pkgsfile(self):
    return self.localurl/'packages'

  def get_rpm_version(self, names):
    scan = re.compile('(?:.*/)?(' + '|'.join(names) + ')-(.*)(\..*\..*$)')
    if not self.pkgsfile.exists():
      raise RuntimeError("Unable to compute package version for '%s': "
                         "pkgsfile '%s' does not exist."
                         % (names, self.pkgsfile))
    for rpm in self.pkgsfile.read_lines():
      match = scan.match(rpm)
      if match:
        try:
          return match.groups()[0:2]
        except (AttributeError, IndexError):
          pass
    return (None, None)

class RepoEventMixin:
  def __init__(self):
    self.repos = RepoContainer()

  def setup_repos(self, type, distro, version,
                        baseurl=None, mirrorlist=None,
                        baseurl_prefix=None, mirrorlist_prefix=None,
                        updates=None, read_md=True, cls=SpinRepo):
    repos = RepoContainer()
    if distro and version:
      # get one of the default distro/version RepoContainers
      try:
        repos.add_repos(getDefaultRepos(type, distro, version,
                                        arch=self.basearch,
                                        baseurl_prefix=baseurl_prefix,
                                        mirrorlist_prefix=mirrorlist_prefix,
                                        cls=cls)
                        or {})
      except KeyError:
        raise ValueError("Unknown default distro-version combo '%s-%s'" % (distro, version))
    if not repos and (baseurl or mirrorlist):
      repos.add_repo(cls(id=type, name=id, baseurl=baseurl, mirrorlist=mirrorlist))

    # update default values
    repos.add_repos(updates or {})

    assert repos # make sure we got at least one repo out of that mess

    for repo in repos.values():
      # remove repo if disabled in repofile
      if hasattr(repo, 'enabled') and repo.enabled in BOOLEANS_FALSE:
        del remoterepos[repo.id]
        continue

      # set pkgsfile
      repo.localurl = self.mddir/repo.id

      if read_md:
        # read metadata
        repo.read_repomd()

        # add metadata to io sync
        paths = []
        for f in repo.datafiles.values():
          paths.append(repo.url / f)
        self.io.add_fpaths(paths, self.mddir/repo.id/'repodata',
                           id='%s-repodata' % repo.id)

    self.repoids = repos.keys()
    self.DATA['variables'].append('repoids')

    self.repos.add_repos(repos)
    return self.repos

  def sync_repodata(self):
    for repo in self.repos.values():
      self.io.sync_input(what='%s-repodata' % repo.id, cache=True,
                         text=("downloading repodata - '%s'" % repo.id))

  def read_packages(self):
    # compute the set of old and new repos
    if self.diff.handlers['variables'].diffdict.has_key('repoids'):
      prev,curr = self.diff.handlers['variables'].diffdict['repoids']
      if not isinstance(prev, list): prev = [] # ugly hack; NewEntry not iterable
      newids = set(curr).difference(prev)
    else:
      newids = set()

    for repo in self.repos.values():
      if not repo.localurl:
        raise RuntimeError("localurl not set for repo '%s' (run self.setup_repos() first?)" % (repo.id))

      pxml = repo.localurl//repo.datafiles['primary']

      # if the input primary.xml has changed or if the repo id wasn't in the
      # previous run
      if self.diff.handlers['input'].diffdict.has_key(pxml) or \
         repo.id in newids:
        self.log(2, L2(repo.id))
        repo.read_repocontent_from_xml(repo.localurl)
        repo.write_repocontent_csv(repo.pkgsfile)
        self.DATA['output'].append(repo.pkgsfile) # add pkgsfile to output
