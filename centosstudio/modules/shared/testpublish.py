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
from centosstudio.event     import Event
from centosstudio.cslogging import L1, L2
from centosstudio.util      import pps

from centosstudio.modules.shared import RepomdMixin
from centosstudio.modules.shared import PublishSetupEventMixin
from centosstudio.modules.shared import ReleaseRpmEventMixin
from centosstudio.modules.shared import KickstartEventMixin

class TestPublishEventMixin(ReleaseRpmEventMixin, 
                            RepomdMixin, KickstartEventMixin, 
                            PublishSetupEventMixin):
  def __init__(self, *args, **kwargs):

    self.DATA =  {
      'config':    [],
      'input':     [],
      'output':    [],
      'variables': [],
    }

    ReleaseRpmEventMixin.__init__(self, rpmxpath='/*/release-rpm')
    RepomdMixin.__init__(self)
    KickstartEventMixin.__init__(self)
    PublishSetupEventMixin.__init__(self)

    self.conditionally_requires.update(['release-rpm-name', 'rpmbuild-data'])

  def setup(self):
    self.diff.setup(self.DATA)
    PublishSetupEventMixin.setup(self)
    self.release_rpmdata = (self.cvars['rpmbuild-data']
                            [self.cvars['release-rpm-name']])

    # sync compose output, excluding release-rpm
    release_rpm = self.release_rpmdata['rpm-path'].split('/')[-1]
    paths=self.cvars['os-dir'].findpaths(nglob=release_rpm, 
                                         type=pps.constants.TYPE_NOT_DIR)
    for p in paths:
      dirname =  '/'.join(p.split('/')
                 [len(self.REPO_STORE.split('/')):])
      self.io.add_item(p, self.REPO_STORE/dirname, id='os-dir')

    # release-rpm
    try:
      self.release = self.release_rpmdata['rpm-release']
      ReleaseRpmEventMixin.setup(self, webpath=self.webpath, 
                         release=self.release,
                         files_cb=self.link_callback, 
                         files_text=self.log(4, L2(
                           "gathering release-rpm content")))
      self.DATA['variables'].append('release')
    except KeyError:
      # release rpm not created
      pass

    # kickstart 
    self.ksxpath = 'kickstart'
    if self.config.get('kickstart', None) is not None: # test ks provided
      KickstartEventMixin.setup(self)
    elif 'ks-path' in self.cvars:
      self.kstext = self.cvars['kickstart-file'].read_text() # production ks provided
    else:
      self.kstext = ''

  def run(self): 
    #clean publish path if event was forced
    if self.forced:
      self.localpath.rm(recursive=True, force=True)

    # sync files from compose (os-dir) folder
    self.REPO_STORE.rm(force=True)
    self.io.process_files(link=True, text="preparing %s repository" 
                          % self.moduleid, what='os-dir')

    # modify release-rpm
    try:
      release = self.release_rpmdata['rpm-release']
    except KeyError: # release-rpm does not exist, no need to modify
      pass
    else: # release-rpm exists, modify it
      ReleaseRpmEventMixin.run(self)
      self.rpm.rpm_path.cp(self.REPO_STORE/'Packages')
      self.DATA['output'].append(self.REPO_STORE/'Packages'/
                                 self.rpm.rpm_path.basename)

    # update repodata
    self.createrepo(self.REPO_STORE/'Packages', 
                    groupfile=self.cvars['groupfile'],
                    checksum=self.locals.L_CHECKSUM['type'])
    self.repomdfile = self.REPO_STORE/'repodata/repomd.xml'

    # update kickstart
    if self.config.get('kickstart', None) is not None:
      (self.REPO_STORE/'ks.cfg').rm(force=True)
      KickstartEventMixin.run(self) 

    # publish to test folder
    self.log(2, L1('publishing to %s' % self.localpath))
    self.localpath.rm(force=True)
    self.link(self.REPO_STORE, self.localpath) 
    self.io.chcon(self.localpath)

  def apply(self):
    self.cvars['%s-kstext' % self.moduleid] = self.kstext # provided by ks mixin
    self.cvars['%s-repomdfile' % self.moduleid] = self.repomdfile # provided by repomdmixin

  def verify_repomdfile(self):
    "verify repomd file exists"
    self.verifier.failUnlessExists(self.repomdfile)

  def verify_cvars(self):
    "verify cvars exist"
    self.verifier.failUnlessSet('%s-kstext' % self.moduleid)
    self.verifier.failUnlessSet('%s-repomdfile' % self.moduleid)
