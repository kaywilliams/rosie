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
import os

from centosstudio.util import mkrpm
from centosstudio.util import shlib
from centosstudio.util import repo

from centosstudio.event   import Event
from centosstudio.cslogging import L1, L2

from centosstudio.modules.shared import comps
from centosstudio.modules.shared import CentOSStudioRepoGroup

from centosstudio.util.repo.repo import RepoContainer

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['RpmbuildRepoEvent'],
  description = 'creates repository metadata for rpmbuild RPMs',
  group       = 'rpmbuild',
)

class RpmbuildRepoEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'rpmbuild-repo',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = 1.02,
      suppress_run_message = True,
      requires = ['rpmbuild-data', ],
      conditionally_requires = ['gpg-signing-keys', 'comps-object'],
      provides = ['repos', 'source-repos', 'comps-object']
    )

    self.cid =  '%s' % self.solutionid
    self.csid = '%s-sources' % self.solutionid

    self.RPMBUILD_RPMS  = self.mddir/self.cid
    self.RPMBUILD_SRPMS = self.mddir/self.csid

    self.DATA = {
      'input':     [],
      'output':    [],
      'variables': [],
    }

    self.repos = RepoContainer()

  def setup(self):
    self.diff.setup(self.DATA)

    if 'gpg-signing-keys' in self.cvars:
      self.pubkey = self.cvars['gpg-signing-keys']['pubkey']
      self.DATA['input'].append(self.cvars['gpg-signing-keys']['pubkey'])
    else:
      self.pubkey = ''

    if self.cvars['rpmbuild-data']:
      for id in self.cvars['rpmbuild-data'].keys():
        self.io.add_fpath(self.cvars['rpmbuild-data'][id]['rpm-path'],
                          self.RPMBUILD_RPMS, id='rpmbuild-rpms')
        self.io.add_fpath(self.cvars['rpmbuild-data'][id]['srpm-path'],
                          self.RPMBUILD_SRPMS, id='rpmbuild-srpms')

      rpmbuild_rpms  = CentOSStudioRepoGroup(id=self.cid, name=self.cid,
                              baseurl=self.RPMBUILD_RPMS, gpgcheck='yes',
                              gpgkey='file://%s' % self.pubkey,)
      rpmbuild_srpms = CentOSStudioRepoGroup(id=self.csid, name=self.csid,
                                   baseurl=self.RPMBUILD_SRPMS)

      self._setup_repos('packages', updates = {self.cid:  rpmbuild_rpms,
                                               self.csid: rpmbuild_srpms})

  def run(self):
    # remove previous output
    self.io.clean_eventcache(all=True)

    # sync rpms
    self.log(4, L1("copying packages"))
    if self.cvars['rpmbuild-data']:
      self.io.process_files(what='rpmbuild-rpms', callback=self.link_callback,
                         text=self.log(4, L2("Linking RPMS")))
      self.io.process_files(what='rpmbuild-srpms', callback=self.link_callback,
                         text=self.log(4, L2("Linking SRPMS")))

    # run createrepo
    self.log(4, L1("creating repository metadata"))
    if self.cvars['rpmbuild-data']:
      for repo in self.repos.values():
        self.log(4, L2(repo.id))
        self._createrepo(repo.localurl)
        repo.read_repomd()
        repo.repocontent.clear()
        for pxml in repo.datafiles['primary']:
          repo.repocontent.update(pxml.href, clear=False)
        self.DATA['output'].append(repo.localurl/'repodata')

  def apply(self):
    if not 'comps-object' in self.cvars:
      self.cvars['comps-object'] = comps.Comps()
      self.cvars['comps-object'].add_core_group()

    self._populate()
    if self.cvars['rpmbuild-data']:
      self.cvars['repos'].add_repo(self.repos[self.cid])

  def verify_repodata(self):
    "repodata exists"
    if self.cvars['rpmbuild-rpms']:
      rpmbuildrepo = self.repos[self.cid]
      self.verifier.failUnlessExists(rpmbuildrepo.url / rpmbuildrepo.repomdfile)
      self.verifier.failUnlessExists(rpmbuildrepo.url / rpmbuildrepo.datafiles['primary'].href)
    if self.cvars['rpmbuild-srpms']:
      rpmbuildrepo = self.repos[self.csid]
      self.verifier.failUnlessExists(rpmbuildrepo.url / rpmbuildrepo.repomdfile)
      self.verifier.failUnlessExists(rpmbuildrepo.url / rpmbuildrepo.datafiles['primary'].href)

  #----- HELPER METHODS -----#
  def _createrepo(self, path):
    # createrepo
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo --update -q .')
    os.chdir(cwd)

  def _populate(self):
    if not self.cvars.has_key('rpmbuild-data'): return

    core_group = self.cvars['comps-object'].return_group('core')

    for v in self.cvars['rpmbuild-data'].values():
      core_group.add_package( package=v['rpm-name'], 
                              genre=v['packagereq-type'],
                              requires=v['packagereq-requires'],
                              default=v['packagereq-default'])
      if v['rpm-obsoletes']:
        for package in v['rpm-obsoletes']:
          self.cvars['comps-object'].remove_package(package)

  def _setup_repos(self, type, updates=None):

    repos = RepoContainer()

    # update default values
    repos.add_repos(updates or {})

    for repo in repos.values():
      # set pkgsfile
      repo.localurl = self.mddir/repo.id

    # make sure we got at least one repo out of that mess
    if not len(repos) > 0:
      raise RuntimeError(
        "Got no repos out of .setup_repos() for repo type '%s'" % type)

    self.repoids = repos.keys()

    self.repos.add_repos(repos)
    return self.repos
