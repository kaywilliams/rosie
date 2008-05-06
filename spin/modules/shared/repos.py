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
from rendition import pps

from spin.logging   import L1, L2
from spin.repo      import RepoContainer
from spin.constants import BOOLEANS_FALSE

__all__ = ['RepoEventMixin']

class RepoEventMixin:
  def __init__(self):
    self.repocontainer = RepoContainer(self)

  def read_config(self, repos=None, files=None):
    # one or the other of repos or files is required by validation
    if repos:
      for repoxml in self.config.xpath(repos, []):
        id = repoxml.get('@id')
        self.repocontainer.add_repo(id)
        self.repocontainer[id].read_config(repoxml)

    if files:
      for filexml in self.config.xpath(files, []):
        self.repocontainer.read(filexml.text)

    for repo in self.repocontainer.values():
      # remove repo if disabled in repofile
      if repo.has_key('enabled') and repo['enabled'] in BOOLEANS_FALSE:
        self.repocontainer.pop(repo.id)
        continue

      for key in repo.keys():
        for yumvar in ['$releasever', '$arch', '$basearch', '$YUM']:
          if not repo[key].find(yumvar) == -1:
            raise ValueError("The definition for repository '%s' contains "
            "yum variable '%s' in the '%s' element. Yum variables (e.g. "
            "$releasever, $arch, $basearch, and $YUM0 - $YUM9) are ambiguous "
            "in the distribution build context. For example, should $releasever "
            "be the release number of the machine you are building on, the "
            "distribution you are building, or base repository you are using? "
            "Replace yum variables with fixed values and try again."
            % (repo.id, yumvar, key))

      repo.localurl = self.mddir/repo.id
      repo.pkgsfile = self.mddir/repo.id/'packages'

      if repo.id == self.cvars['base-repoid']:
        folder = 'images'
        args = {'glob': folder,
                'type': pps.constants.TYPE_DIR,
                'mindepth': 1,
                'maxdepth': 1}
        if repo.remoteurl.findpaths(**args):
          repo.osdir = repo.remoteurl
        elif repo.remoteurl.dirname.findpaths(**args):
          repo.osdir = repo.remoteurl.dirname
        else:
          raise RuntimeError("Unable to find a folder named '%s' at '%s' "
          "or '%s'. Check the baseurl for the '%s' repo, or specify an alternative "
          "base-repo, and try again."
          % (folder, repo.remoteurl, repo.remoteurl.dirname, repo.id))

      repo._read_repodata()

      paths = []
      for filetype in repo.datafiles.keys():
        paths.append(repo.remoteurl / \
                     'repodata' / \
                     repo.datafiles[filetype])
      paths.append(repo.remoteurl/repo.mdfile)
      self.io.add_fpaths(paths, repo.localurl/'repodata',
                         id='%s-repodata' % repo.id)

    self.repoids = self.repocontainer.keys()
    self.DATA['variables'].append('repoids')

  def sync_repodata(self):
    for repo in self.repocontainer.values():
      self.io.sync_input(what='%s-repodata' % repo.id, cache=True,
                         text=("downloading repodata - '%s'" % repo.id))

  def read_new_packages(self):
    for repo in self.repocontainer.values():
      pxml = repo.remoteurl/'repodata'/repo.datafiles['primary']
      # determine if the repo has a new id
      newid = False
      if self.diff.handlers['variables'].diffdict.has_key('repoids'):
        old,new = self.diff.handlers['variables'].diffdict['repoids']
        if not hasattr(old, '__iter__'): old = []
        newid = repo.id in set(new).difference(set(old))
      if self.diff.handlers['input'].diffdict.has_key(pxml) or newid:
        self.log(2, L2(repo.id))
        repo._read_repo_content()
        repo.write_repo_content(repo.pkgsfile)
      self.DATA['output'].append(repo.pkgsfile)
