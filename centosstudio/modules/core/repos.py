#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
import ConfigParser

from centosstudio.util.repo    import ReposFromXml, ReposFromFile, RepoContainer, RepoFileParseError
from centosstudio.util.versort import Version

from centosstudio.errors   import assert_file_has_content, assert_file_readable, CentOSStudioEventError
from centosstudio.event    import Event
from centosstudio.cslogging  import L1, L2
from centosstudio.validate import InvalidConfigError

from centosstudio.modules.shared import RepoEventMixin, CentOSStudioRepoGroup, CentOSStudioRepoFileParseError

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ReposEvent'],
  description = 'downloads metadata for input repositories',
)

class ReposEvent(RepoEventMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'repos',
      parentid = 'setup-events',
      ptr = ptr,
      version = 1.3,
      provides = ['anaconda-version', 
                  'repos', 'installer-repo', 'base-treeinfo',
                  'input-repos', # ugly solution to cycle in rpmbuild-repo
                  ],
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
      updates.add_repos(ReposFromXml(self.config.get('.'), cls=CentOSStudioRepoGroup))
    for filexml in self.config.xpath('repofile/text()', []):
      fn = self.io.abspath(filexml)
      assert_file_has_content(fn)
      try:
        updates.add_repos(ReposFromFile(fn, cls=CentOSStudioRepoGroup))
      except RepoFileParseError, e:
        raise CentOSStudioRepoFileParseError(e.args[0])

    self.setup_repos(updates)
    self.read_repodata()

  def run(self):
    self.sync_repodata()

  def apply(self):

    # set up installer repo
    for repo in self.repos.values():
      if repo.has_installer_files:
        self.cvars['installer-repo'] = repo

        # .treeinfo exists?
        if not (self.mddir/repo.id/repo.treeinfofile).exists():
          raise TreeinfoNotFoundError(repoid=repo.id, repourl=repo.url.realm)   

        # read treeinfo
        else:
          treeinfo = ConfigParser.SafeConfigParser()
          treeinfo.read(self.mddir/repo.id/repo.treeinfofile)

          # supported distribution?
          df = treeinfo.get('general', 'family')
          dv = treeinfo.get('general', 'version')[:1]
          supported = False
          for d in ['CentOS', 'Red Hat Enterprise Linux']:
            if d in df and dv in ['5','6']:
              supported = True
          if not supported: 
            raise UnsupportedInstallerRepoError(repoid=repo.id, 
                  family=df, 
                  version=treeinfo.get('general', 'version'), 
                  repourl=repo.url.realm)

          # set base-treeinfo control variable
          self.cvars['base-treeinfo'] = treeinfo

          # set anaconda version
          self.cvars['anaconda-version'] = self.locals.L_ANACONDA_VERSION
      
    if not self.cvars['installer-repo']:
      raise InstallerRepoNotFoundError()

    # set up cvars
    self.cvars['repos']   = self.repos
    self.cvars['repoids'] = self.repoids

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


#------ ERRORS ------#
class InstallerRepoNotFoundError(CentOSStudioEventError):
  message = ( "Unable to find 'isolinux/' and 'images/' folders inside any "
              "given repository." )

class TreeinfoNotFoundError(CentOSStudioEventError):
  message = ( "Unable to find '.treeinfo' file in '%(repoid)s' repo "
              "at '%(repourl)s' " )

class UnsupportedInstallerRepoError(CentOSStudioEventError):
  message = ( "The '%(repoid)s' repository containing '%(family)s %(version)s' "
              "at '%(repourl)s' is not supported." )
