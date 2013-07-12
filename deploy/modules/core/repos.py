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
import re
import ConfigParser

from deploy.util.repo    import (ReposFromXml, ReposFromFile, RepoContainer,
                                RepoFileParseError)

from deploy.util.versort import Version

from deploy.errors   import (assert_file_has_content, assert_file_readable,
                             DeployEventError)
from deploy.event    import Event
from deploy.dlogging  import L1, L2
from deploy.validate import InvalidConfigError

from deploy.modules.shared import RepoEventMixin, DeployRepoGroup, DeployRepoFileParseError

def get_module_info(ptr, *args, **kwargs):
  return dict(
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
                  'base-treeinfo-text'
                  'input-repos', # ugly solution to cycle in rpmbuild-repo
                  ],
      conditionally_requires = [ 'repos' ]
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

    updates  = self.cvars.get('repos', RepoContainer())
    if self.config.pathexists('.'):
      updates.add_repos(ReposFromXml(self.config.getxpath('.'),
                                     cls=DeployRepoGroup,
                                     ignore_duplicates=True,
                                     locals=self.locals),
                        ignore_duplicates=True)

    for filexml in self.config.xpath('repofile/text()', []):
      fn = self.io.abspath(filexml)
      assert_file_has_content(fn)
      try:
        updates.add_repos(ReposFromFile(fn, cls=DeployRepoGroup,
                                            ignore_duplicates=True,
                                            locals=self.locals),
                          ignore_duplicates=True)
      except RepoFileParseError, e:
        raise DeployRepoFileParseError(e.args[0])

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
          raise TreeinfoNotFoundError(repoid=repo.id, repourl=repo.url.touri())   

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

          # set base-treeinfo control variables
          self.cvars['base-treeinfo'] = treeinfo
          self.cvars['base-treeinfo-text'] = ( 
            (self.mddir/repo.id/repo.treeinfofile).read_text().rstrip())

          # set anaconda version
          self.cvars['anaconda-version'] = self.locals.L_ANACONDA_VERSION
      
    if self.type == "system" and not self.cvars['installer-repo']:
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
    if self.type == "system":
      self.verifier.failUnlessSet('anaconda-version')
      self.verifier.failUnlessSet('installer-repo')


#------ ERRORS ------#
class InstallerRepoNotFoundError(DeployEventError):
  message = ( "Unable to find 'isolinux/' and 'images/' folders inside any "
              "given repository. In system mode, at least one operating "
              "system repository must be specified.")

class TreeinfoNotFoundError(DeployEventError):
  message = ( "Unable to find '.treeinfo' file in '%(repoid)s' repo "
              "at '%(repourl)s' " )

class UnsupportedInstallerRepoError(DeployEventError):
  message = ( "The '%(repoid)s' repository containing '%(family)s %(version)s' "
              "at '%(repourl)s' is not supported." )
