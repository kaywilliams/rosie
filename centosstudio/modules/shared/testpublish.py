#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
from centosstudio.modules.shared import ConfigEventMixin
from centosstudio.modules.shared import KickstartEventMixin

class TestPublishEventMixin(ConfigEventMixin, RepomdMixin, KickstartEventMixin, 
                            PublishSetupEventMixin):
  def __init__(self):

    self.configxpath = 'config'

    self.DATA =  {
      'config':    [],
      'input':     [],
      'output':    [],
      'variables': [],
    }

    ConfigEventMixin.__init__(self)
    RepomdMixin.__init__(self)
    KickstartEventMixin.__init__(self)
    PublishSetupEventMixin.__init__(self)

  def clean(self):
    Event.clean(self)
    self.localpath.rm(recursive=True, force=True) #publish path

  def setup(self):
    self.diff.setup(self.DATA)

    # sync compose output, excluding system-config rpm
    config_rpm=self.cvars['rpmbuild-data']['config']['rpm-path'].split('/')[-1]
    paths=self.cvars['os-dir'].findpaths(nglob=config_rpm, 
                                         type=pps.constants.TYPE_NOT_DIR)
    for p in paths:
      dirname =  '/'.join(p.split('/')
                 [len(self.SOFTWARE_STORE.split('/')):])
      self.io.add_item(p, self.SOFTWARE_STORE/dirname, id='os-dir')

    # config-rpm
    if 'config-release' in self.cvars:
      ConfigEventMixin.setup(self, webpath=self.webpath, 
                         release=self.cvars['config-release'],
                         files_cb=self.link_callback, 
                         files_text=self.log(4, L2("gathering config content")))
      self.DATA['variables'].append('cvars[\'config-release\']')

    # kickstart 
    self.ksxpath = 'kickstart'
    if self.config.get('kickstart', None) is not None: # test ks provided
      KickstartEventMixin.setup(self)
    elif 'ks-path' in self.cvars:
      self.kstext = self.cvars['kickstart-file'].read_text() # production ks provided
    else:
      self.kstext = ''


  def run(self):
    # sync files from compose (os-dir) folder
    self.SOFTWARE_STORE.rm(force=True)
    self.io.process_files(link=True, text="preparing %s repository" 
                          % self.moduleid, what='os-dir')

    # modify config-rpm
    if 'config-release' in self.cvars:
      ConfigEventMixin.run(self)
      (self.rpm.rpm_path).cp(self.SOFTWARE_STORE/'Packages')
      self.DATA['output'].append(self.SOFTWARE_STORE/'Packages'/
                                 self.rpm.rpm_path.basename)

    # update repodata
    self.createrepo(self.SOFTWARE_STORE, 
                    groupfile=self.cvars['groupfile'],
                    checksum=self.locals.L_CHECKSUM['type'])
    self.repomdfile = self.SOFTWARE_STORE/'repodata/repomd.xml'

    # update kickstart
    if self.config.get('kickstart', None) is not None:
      (self.SOFTWARE_STORE/'ks.cfg').rm(force=True)
      KickstartEventMixin.run(self) 

    # publish to test folder
    self.log(2, L1('publishing to %s' % self.localpath))
    self.localpath.rm(force=True)
    self.link(self.SOFTWARE_STORE, self.localpath) 
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
