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
import os

from rendition import shlib
from rendition import repo

from spin.event   import Event
from spin.logging import L1, L2

from spin.modules.shared import SpinRepo, RepoEventMixin

API_VERSION = 5.0

EVENTS = {'rpms': ['CustomRepoEvent']}

class CustomRepoEvent(RepoEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'custom-repo',
      conditionally_requires = ['custom-rpms-data', 'base-info-distro'],
      provides = ['repos', 'source-repos',
                  'comps-included-packages',
                  'comps-excluded-packages']
    )

    self.cid =  'custom-repo'
    self.csid = 'custom-repo-sources'

    self.CUSTOM_RPMS  = self.mddir/self.cid
    self.CUSTOM_SRPMS = self.mddir/self.csid

    self.DATA = {
      'input':  [],
      'output': [],
      'variables': [],
    }

    RepoEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    if self.cvars['custom-rpms-data']:
      for id in self.cvars['custom-rpms-data'].keys():
        self.io.add_fpath(self.cvars['custom-rpms-data'][id]['rpm-path'],
                          self.CUSTOM_RPMS, id='custom-rpms')
        self.io.add_fpath(self.cvars['custom-rpms-data'][id]['srpm-path'],
                          self.CUSTOM_SRPMS, id='custom-rpms')

      custom_rpms  = SpinRepo(id=self.cid,  name=self.cid,  baseurl=self.CUSTOM_RPMS)
      custom_srpms = SpinRepo(id=self.csid, name=self.csid, baseurl=self.CUSTOM_SRPMS)

      self.setup_repos('packages', defaults=False,
                       updates = {self.cid:  custom_rpms,
                                  self.csid: custom_srpms})

  def run(self):
    # remove previous output
    self.io.clean_eventcache(all=True)

    # sync rpms
    self.log(1, L1("copying packages"))
    if self.cvars['custom-rpms-data']:
      self.io.sync_input(link=True, what='custom-rpms',
                         text=self.log(4, L2("RPMS")))
      self.io.sync_input(link=True, what='custom-srpms',
                         text=self.log(4, L2("SRPMS")))

    self.log(1, L1("running createrepo"))
    if self.cvars['custom-rpms-data']:
      for repo in self.repos.values():
        self.log(4, L2(repo.id))
        self._createrepo(repo.localurl)
        repo.read_repomd()
        repo.repocontent.update(repo.localurl/repo.datafiles['primary'])
        repo.repocontent.write(repo.pkgsfile)
        self.DATA['output'].append(repo.localurl/'repodata')
        self.DATA['output'].append(repo.pkgsfile)

  def apply(self):
    self.io.clean_eventcache()
    self._populate()
    if self.cvars['custom-rpms-data']:
      try:
        self.repos[self.cid].repocontent.read(self.repos[self.cid].pkgsfile)
      except Exception, e:
        raise RuntimeError(str(e))

      self.cvars['repos'].add_repo(self.repos[self.cid])

      if self.cvars['source-repos']:
        self.repos[self.csid].repocontent.read(self.repos[self.csid].pkgsfile)
        self.cvars['source-repos'].add_repo(self.repos[self.csid])

  def verify_repodata(self):
    "repodata exists"
    if self.cvars['custom-rpms']:
      customrepo = self.repos[self.cid]
      self.verifier.failUnlessExists(customrepo.url / customrepo.repomd)
      self.verifier.failUnlessExists(customrepo.url / customrepo.datafiles['primary'])
    if self.cvars['custom-srpms']:
      customrepo = self.repos[self.csid]
      self.verifier.failUnlessExists(customrepo.url / customrepo.repomd)
      self.verifier.failUnlessExists(customrepo.url / customrepo.datafiles['primary'])

  #----- HELPER METHODS -----#
  def _createrepo(self, path):
    # createrepo
    cwd = os.getcwd()
    os.chdir(path)
    shlib.execute('/usr/bin/createrepo --update -q .')
    os.chdir(cwd)

  def _populate(self):
    if not self.cvars.has_key('custom-rpms-data'): return

    for id in self.cvars['custom-rpms-data'].keys():
      default   = self.cvars['custom-rpms-data'][id]['packagereq-default']
      requires  = self.cvars['custom-rpms-data'][id]['packagereq-requires']
      type      = self.cvars['custom-rpms-data'][id]['packagereq-type']
      rpm_name  = self.cvars['custom-rpms-data'][id]['rpm-name']
      obsoletes = self.cvars['custom-rpms-data'][id]['rpm-obsoletes']
      (self.cvars.setdefault('comps-included-packages', set())
         .add((rpm_name, type, requires, default)))
      if obsoletes:
        self.cvars.setdefault('comps-excluded-packages', set()).update(obsoletes)
