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

from rendition.repo    import ReposFromXml, ReposFromFile, RepoContainer
from rendition.versort import Version

from spin.errors   import assert_file_readable, SpinError
from spin.event    import Event
from spin.logging  import L1, L2
from spin.validate import InvalidConfigError

from spin.modules.shared import RepoEventMixin, SpinRepoGroup

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ReposEvent'],
  description = 'downloads metadata for input repositories',
)

class ReposEvent(RepoEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'repos',
      parentid = 'setup',
      version = 3,
      provides = ['anaconda-version',
                  'logos-versions',
                  'release-versions',
                  'repos',
                  'repos', 'installer-repo',
                  'input-repos', # ugly solution to cycle in release-rpm, rpmbuild-repo
                  'comps-excluded-packages',
                  'pkglist-excluded-packages'],
      conditionally_requires = ['anaconda-version-supplied'],
    )

    RepoEventMixin.__init__(self)

    self.DATA = {
      'variables': [], # stuff added in .setup_repos()
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    updates  = RepoContainer()
    if self.config.pathexists('.'):
      updates.add_repos(ReposFromXml(self.config.get('.'), cls=SpinRepoGroup))
    for filexml in self.config.xpath('repofile/text()', []):
      updates.add_repos(ReposFromFile(self._config.file.dirname/filexml,
                                      cls=SpinRepoGroup))

    self.setup_repos(updates)
    self.read_repodata()

  def run(self):
    self.sync_repodata()

    # process available package lists
    self.log(1, L1("reading available packages"))
    self.read_packages()

  def apply(self):
    self.io.clean_eventcache()

    anaconda_version = None

    for repo in self.repos.values():
      # read repocontent
      assert_file_readable(repo.pkgsfile)
      repo.repocontent.read(repo.pkgsfile)

      # get logos and release versions, if any in repo
      for pkgid,allpkgs in RPMDATA.items(): # see below
        n,v = repo.get_rpm_version(allpkgs)
        if n is not None and v is not None:
          self.cvars.setdefault(pkgid, []).append((n,'==',v))

      # get anaconda version
      n,v = repo.get_rpm_version(['anaconda'])
      if n and v:
        if not anaconda_version or v > anaconda_version:
          anaconda_version = v

    self.cvars['anaconda-version'] = \
      self.cvars['anaconda-version-supplied'] or anaconda_version
    if not self.cvars['anaconda-version']:
      raise AnacondaNotFoundError()

    # set up the installer repo
    for repo in self.repos.values():
      if repo.has_installer_files:
        self.cvars['installer-repo'] = repo
        break

    if not self.cvars['installer-repo']:
      raise InstallerRepoNotFoundError()

    # set up cvars
    self.cvars['repos']   = self.repos
    self.cvars['repoids'] = self.repoids

    # globally excluded packages
    global_excludes = self.config.xpath('exclude-package/text()', [])
    self.cvars.setdefault('comps-excluded-packages', set()).update(global_excludes)
    self.cvars.setdefault('pkglist-excluded-packages', set()).update(global_excludes)

  def verify_pkgsfiles_exist(self):
    "verify all pkgsfiles exist"
    for repo in self.repos.values():
      self.verifier.failUnlessExists(repo.pkgsfile)

  def verify_repodata(self):
    "repodata exists"
    for repogroup in self.repos.values():
      for repo in repogroup.subrepos.values():
        for fn in repo.datafiles.values():
          self.verifier.failUnlessExists(repogroup.localurl/repo._relpath/fn)

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnlessSet('repos')
    self.verifier.failUnlessSet('anaconda-version')
    self.verifier.failUnlessSet('installer-repo')

#------ ERRORS ------#
class AnacondaNotFoundError(SpinError):
  message = "Unable to find the 'anaconda' package in any specified repository"

class InstallerRepoNotFoundError(SpinError):
  message = ( "Unable to find 'isolinux/' and 'images/' folders inside any "
              "given repository." )


#------ LOCALS ------#
# maps an rpm type to the names of rpms for the 'category'
RPMDATA = { 'logos-versions':   [ 'fedora-logos',
                                  'centos-logos',
                                  'redhat-logos' ],
            'release-versions': [ 'fedora-release',
                                  'centos-release',
                                  'redhat-release',
                                  'fedora-release-notes',
                                  'centos-release-notes',
                                  'redhat-release-notes' ] }
