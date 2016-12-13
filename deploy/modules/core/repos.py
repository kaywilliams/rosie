#
# Copyright (c) 2015
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

from deploy.main import DIST_TAG

from deploy.util.repo    import (ReposFromXml, ReposFromFile, RepoContainer,
                                 RepoFileParseError, RepoValidationError)

from deploy.util.versort import Version

from deploy.errors   import (assert_file_has_content, assert_file_readable,
                             DeployEventError)
from deploy.event    import Event
from deploy.dlogging  import L1, L2
from deploy.validate import InvalidConfigError

from deploy.modules.shared import RepoEventMixin, DeployRepoGroup, DeployRepoFileParseError

# map treeinfo family to deploy os
OS = {
  'CentOS Linux':             'centos',
  'CentOS':                   'centos',
  'Red Hat Enterprise Linux': 'rhel',
  'Fedora':                   'fedora',
  }

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
      provides = ['dist-tag', 'anaconda-version',
                  'repos', 'installer-repo', 'base-treeinfo',
                  'input-repos', # ugly solution to cycle in rpmbuild-repo
                  ],
      conditionally_requires = [ 'repos' ]
    )

    self.DATA = {
      'variables': set(), # stuff added in .setup_repos()
      'config':    set(['.']),
      'input':     set(),
      'output':    set(),
    }

    RepoEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    RepoEventMixin.setup(self)

    try:
      if self.config.pathexists('.'):
        self.repos.add_repos(ReposFromXml(self.config.getxpath('.'),
                                          cls=DeployRepoGroup,
                                          ignore_duplicates=True,
                                          locals=self.locals),
                             ignore_duplicates=True)

      for filexml in self.config.xpath('repofile/text()', []):
        fn = self.io.abspath(filexml)
        assert_file_has_content(fn)
        try:
          self.repos.add_repos(ReposFromFile(fn, cls=DeployRepoGroup,
                                             ignore_duplicates=True,
                                             locals=self.locals),
                               ignore_duplicates=True)
        except RepoFileParseError, e:
          raise DeployRepoFileParseError(e.args[0])
    except RepoValidationError, e:
      raise DeployRepoValidationError(msg=e) 

    self.setup_repos(self.repos)
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

          # does treeinfo match specified os-version-arch?
          os = OS[treeinfo.get('general', 'family')]
          version = treeinfo.get('general', 'version').split('.')[0]
          arch = treeinfo.get('general', 'arch')

          if (not version == 'rawhide' and 
              not [os, version, arch] == [self.os, self.version, self.arch]): 
            raise InstallerRepoMismatchError(repoid=repo.id, 
                  repourl=repo.url.touri(), tree_os=os, tree_version=version,
                  tree_arch=arch, os=self.os, version=self.version, 
                  arch=self.arch)

          # set base-treeinfo control variables
          self.cvars['base-treeinfo'] = treeinfo

          # set anaconda version
          self.cvars['dist-tag'] = DIST_TAG[self.os] 
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
class DeployRepoValidationError(DeployEventError):
  message = "%(msg)s"

class InstallerRepoNotFoundError(DeployEventError):
  message = ( "Unable to find an 'images/' folder inside any repository. "
              "In system mode, at least one operating system repository "
              "must be specified.")

class TreeinfoNotFoundError(DeployEventError):
  message = ( "Unable to find '.treeinfo' file in '%(repoid)s' repo "
              "at '%(repourl)s' " )

class InstallerRepoMismatchError(DeployEventError):
  message = ( "The tree information ('%(tree_os)s-%(tree_version)s-"
              "%(tree_arch)s') for installer repository '%(repoid)s' "
              "at '%(repourl)s'  does not match the specified operating "
              "system ('%(os)s-%(version)s-%(arch)s').")
