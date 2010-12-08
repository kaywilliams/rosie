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
import re

from systembuilder.util.repo    import ReposFromXml, ReposFromFile, RepoContainer, RepoFileParseError
from systembuilder.util.versort import Version

from systembuilder.errors   import assert_file_has_content, assert_file_readable, SystemBuilderError
from systembuilder.event    import Event
from systembuilder.logging  import L1, L2
from systembuilder.validate import InvalidConfigError

from systembuilder.modules.shared import RepoEventMixin, SystemBuilderRepoGroup, SystemBuilderRepoFileParseError

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
                  'input-repos', # ugly solution to cycle in rpmbuild-repo
                  'excluded-packages',
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
      updates.add_repos(ReposFromXml(self.config.get('.'), cls=SystemBuilderRepoGroup))
    for filexml in self.config.xpath('repofile/text()', []):
      fn = self.io.abspath(filexml)
      assert_file_has_content(fn)
      try:
        updates.add_repos(ReposFromFile(fn, cls=SystemBuilderRepoGroup))
      except RepoFileParseError, e:
        raise SystemBuilderRepoFileParseError(e.args[0])

    self.setup_repos(updates)
    self.read_repodata()

  def run(self):
    self.sync_repodata()

    # process available package lists
    self.log(1, L1("reading available packages"))
    self.read_packages()

  def apply(self):
    self.io.clean_eventcache()

    # read repocontent
    for repo in self.repos.values():
      assert_file_readable(repo.pkgsfile)
      repo.repocontent.read(repo.pkgsfile)

    if self.cvars['system-info']['anaconda-version'] is not None:
      self.cvars['anaconda-version'] = self.cvars['system-info']['anaconda-version']
    else:
      anaconda_version = self._get_anaconda_version()
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
    global_excludes = self.config.xpath('exclude/text()', [])
    self.cvars.setdefault('excluded-packages', set()).update(global_excludes)
    self.cvars.setdefault('pkglist-excluded-packages', set()).update(global_excludes)

  def verify_pkgsfiles_exist(self):
    "verify all pkgsfiles exist"
    for repo in self.repos.values():
      self.verifier.failUnlessExists(repo.pkgsfile)

  def verify_repodata(self):
    "repodata exists"
    for repo in self.repos.values():
      for subrepo in repo.subrepos.values():
        for datafile in subrepo.iterdatafiles():
          self.verifier.failUnlessExists(
            self.mddir/repo.id/subrepo._relpath/datafile.href)

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnlessSet('repos')
    self.verifier.failUnlessSet('anaconda-version')
    self.verifier.failUnlessSet('installer-repo')

  def _get_anaconda_version(self):
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

    return anaconda_version


#------ ERRORS ------#
class AnacondaNotFoundError(SystemBuilderError):
  message = "Unable to find the 'anaconda' package in any specified repository"

class InstallerRepoNotFoundError(SystemBuilderError):
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
