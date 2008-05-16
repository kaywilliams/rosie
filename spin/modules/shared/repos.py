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

  def _pkg_filter(self, pkg):
    """Returns True if this repo can have the given pkg based on exclude
    and includepkgs.  Doesn't actually check to see if pkg is in the repo."""
    if pkg in self.exclude: return False
    if self.includepkgs: return pkg in self.includepkgs
    return True

  def get_rpm_version(self, names):
    # filter list of names if necessary
    names = [ n for n in names if self._pkg_filter(n) ]
    if not names: return (None, None)

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

  def setup_repos(self, type, distro=None, version=None,
                        baseurl_prefix=None, mirrorlist_prefix=None,
                        updates=None, cls=SpinRepo):
    """
    Populates self.repos with Repo objects from the specified defaults
    combined with any desired updates.  Also sets repo.localurl for each
    repo it creates.  Doesn't include repos that are disabled.  Handles
    setting up self.DATA['variables'] for repoids.  Returns the created
    RepoContainer (self.repos).

    This method should typically be called in Event.setup()

    type    : the type of repos to get using getDefaultRepos(); one of
              'installer', 'packages', or 'source'
    distro  : the distribution name to pass to getDefaultRepos()
    version : the version to pass to getDefaultRepos()
    baseurl_prefix : the prefix to prepend to the default baseurls returned
              by getDefaultRepos(); optional
    mirrorlist_prefix : the prefix to prepend to the default mirrorlists
              returned by getDefaultRepos(); optional
    updates : a RepoContainer or dictionary containing Repos to use as
              updates to the defaults returned by getDefaultRepos().  Repos
              with the same id as those returned by getDefaultRepos() will
              update the value of its elements; those with differing values
              will create new repos entirely; optional
    cls     : the class of repo to use in creating default repos; optional
    """
    # set up arg defaults
    distro  = distro  or self.cvars['base-distro']['distro']
    version = version or self.cvars['base-distro']['version']
    baseurl_prefix    = baseurl_prefix    or \
                        self.cvars['base-distro']['baseurl-prefix']
    mirrorlist_prefix = mirrorlist_prefix or \
                        self.cvars['base-distro']['mirrorlist-prefix']

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

    # update default values
    repos.add_repos(updates or {})

    for repo in repos.values():
      # remove repo if disabled in repofile
      if hasattr(repo, 'enabled') and repo.enabled in BOOLEANS_FALSE:
        del repos[repo.id]
        continue

      # set pkgsfile
      repo.localurl = self.mddir/repo.id

    # make sure we got at least one repo out of that mess
    if not len(repos) > 0:
      raise RuntimeError(
        "Got no repos out of .setup_repos() for repo type '%s'" % type)

    self.repoids = repos.keys()
    self.DATA['variables'].extend(['repoids',
                                   'cvars[\'base-distro\'][\'distro\']',
                                   'cvars[\'base-distro\'][\'version\']',
                                   'cvars[\'base-distro\'][\'baseurl-prefix\']',
                                   'cvars[\'base-distro\'][\'mirrorlist-prefix\']'])

    self.repos.add_repos(repos)
    return self.repos

  def read_repodata(self):
    """
    Reads repository metadata and sets up the necessary IO data structures
    so that repodata can be synced with .sync_repodata(), below.  Sets
    up each repo's .datafiles dictionary and populates self.DATA['input']
    and self.DATA['output'] with these files.

    This method should typically be called in Event.setup(), after
    .setup_repos().  It is only necessary to call this if you want to use
    .sync_repodata(), below, to copy down all repository metadata.
    """
    for repo in self.repos.values():
      # read metadata
      repo.read_repomd()

      # add metadata to io sync
      self.io.add_fpaths([ repo.url/f for f in repo.datafiles.values() ],
                         self.mddir/repo.id/'repodata',
                         id='%s-repodata' % repo.id)

  def sync_repodata(self):
    """
    Synchronizes repository metadata from the primary location to a local
    cache.

    This method should typically be called in Event.run(); it must be
    preceded by a call to .read_repomd(), above.
    """
    for repo in self.repos.values():
      self.io.sync_input(what='%s-repodata' % repo.id, cache=True,
                         text=("downloading repodata - '%s'" % repo.id))

  def read_packages(self):
    """
    After synchronizing repository metadata, this method reads in the list
    of packages, along with size and mtime information about each one, from
    the primary.xml.gz.  This is only done for primary.xml.gz files that
    actually change, or for new repositories.  After reading this data in,
    it is written out to the repository's pkgsfile.

    This method should typically be called in Event.run(), after calling
    .sync_repodata(), above.  Each repo's .localurl attribute must also be
    set (normally handled via .setup_repos(), also above).
    """
    # compute the set of old and new repos
    difftup = self.diff.variables.difference('repoids')
    if difftup:
      prev,curr = difftup
      if not isinstance(prev, list): prev = [] # ugly hack; NewEntry not iterable
      newids = set(curr).difference(prev)
    else:
      newids = set()

    for repo in self.repos.values():
      pxml = repo.localurl//repo.datafiles['primary']

      # if the input primary.xml has changed or if the repo id wasn't in the
      # previous run
      if repo.id in newids or self.diff.input.difference(pxml):
        self.log(2, L2(repo.id))
        repo.repocontent.update(pxml)
        repo.repocontent.write(repo.pkgsfile)

      self.DATA['output'].append(repo.pkgsfile) # add pkgsfile to output
