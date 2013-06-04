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
from deploy.event     import Event, DummyConfig
from deploy.dlogging import L1, L2
from deploy.util      import pps
from deploy.util      import rxml 

from deploy.modules.shared import RepomdMixin
from deploy.modules.shared import PublishSetupEventMixin
from deploy.modules.shared import ReleaseRpmEventMixin
from deploy.modules.shared import KickstartEventMixin

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

    try:
      rpmconf = self.config.getxpath('/*/release-rpm')
    except rxml.errors.XmlPathError:
      rpmconf = DummyConfig(self._config) 

    ReleaseRpmEventMixin.__init__(self, rpmconf=rpmconf)
    RepomdMixin.__init__(self)
    KickstartEventMixin.__init__(self)
    PublishSetupEventMixin.__init__(self)

    self.conditionally_requires.update(['release-rpm', 
                                        'rpmbuild-data',
                                        'publish-ksfile'])
    self.provides.remove('rpmbuild-data') # these release rpms should not
                                          # be included in the core repository

  def setup(self):
    self.diff.setup(self.DATA)
    PublishSetupEventMixin.setup(self)
    # TODO add support for disabled release-rpm event
    self.release_rpmdata = (self.cvars['rpmbuild-data']
                            [self.cvars['release-rpm']])

    # sync compose output, excluding release-rpm and repodata files
    release_rpm = (self.release_rpmdata['rpm-path'].split('/')[-1])
    self.repodata_files = self.cvars['os-dir'] / 'repodata'
    paths=self.cvars['os-dir'].findpaths(nglob=release_rpm, 
                                         nregex='%s/.*' % self.repodata_files,
                                         type=pps.constants.TYPE_NOT_DIR)
    for p in paths:
      dirname =  '/'.join(p.split('/')
                 [len(self.OUTPUT_DIR.split('/')):])
      self.io.add_item(p, self.OUTPUT_DIR/dirname, id='os-dir')

    # release-rpm
    try:
      self.release = self.release_rpmdata['rpm-release'].replace(self.dist, '')
      ReleaseRpmEventMixin.setup(self, webpath=self.webpath, 
                         force_release=self.release,
                         files_cb=self.link_callback, 
                         files_text=self.log(4, L2(
                           "gathering release-rpm content")))
      self.DATA['variables'].append('release')
    except KeyError:
      # release-rpm event disabled
      pass

    # kickstart
    if self.cvars['publish-ksfile']:
      default = self.cvars['publish-ksfile'].read_text()
    else:
      default = ''
    KickstartEventMixin.setup(self, default)

  def run(self): 
    #clean publish path if event was forced
    if self.forced:
      self.localpath.rm(recursive=True, force=True)

    # sync files from compose (os-dir) folder
    self.OUTPUT_DIR.rm(force=True)
    self.io.process_files(link=True, text="preparing %s repository" 
                          % self.moduleid, what='os-dir')

    # modify release-rpm
    (self.OUTPUT_DIR/'repo.conf').rm(force=True) # remove link
    ReleaseRpmEventMixin.run(self)
    self.rpm.rpm_path.cp(self.OUTPUT_DIR/'Packages', force=True, preserve=True)
    self.DATA['output'].append(self.OUTPUT_DIR/'Packages'/
                               self.rpm.rpm_path.basename)

    # update repodata
    self.copy(self.repodata_files, self.OUTPUT_DIR, 
              callback=self.link_callback) # start with existing repodata
    self.createrepo(self.OUTPUT_DIR, 
                    groupfile=self.cvars['groupfile'],
                    checksum=self.locals.L_CHECKSUM['type'])

    # update kickstart
    if self.config.getxpath('kickstart', None) is not None:
      (self.OUTPUT_DIR/self.ksname).rm(force=True)
      KickstartEventMixin.run(self) 

    # publish to test folder
    self.log(2, L1('publishing to %s' % self.localpath))
    self.localpath.rm(force=True)
    self.link(self.OUTPUT_DIR, self.localpath) 
    self.io.chcon(self.localpath)

  def apply(self):
    ReleaseRpmEventMixin.apply(self)
    KickstartEventMixin.apply(self)
