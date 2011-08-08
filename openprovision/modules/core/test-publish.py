#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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

from openprovision.event     import Event, CLASS_META
from openprovision.sslogging import L1, L2
from openprovision.util      import pps

from openprovision.modules.shared import RepomdMixin
from openprovision.modules.shared.config import ConfigEventMixin
from openprovision.modules.shared.kickstart import KickstartEventMixin
from openprovision.modules.shared.publish import PublishEventMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['TestPublishEvent',],
  description = 'creates a test system repository if requested',
)

class TestPublishEvent(ConfigEventMixin, RepomdMixin, KickstartEventMixin, 
                       PublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-publish',
      parentid = 'all',
      version = 1.01,
      requires = ['os-dir'], 
      conditionally_requires = [ 'kickstart-file', 'config-release'],
      provides = ['test-webpath', 'test-repomdfile', 'test-kstext'],
      conditional = True
    )

    self.configxpath = 'config'
    ConfigEventMixin.__init__(self)
    RepomdMixin.__init__(self)
    KickstartEventMixin.__init__(self)

    self.localpath = self.get_local('/var/www/html/system_repos/test')
    self.webpath = self.get_remote('system_repos/test')

    self.DATA =  {
      'config':    ['local-dir', 'remote-url', 'kickstart'],
      'input':     [],
      'output':    [],
      'variables': ['localpath', 'webpath', 'config_mixin_version', 
                    'kickstart_mixin_version'],
    }

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
                         release=self.cvars['config-release'] + '.test',
                         files_cb=self.link_callback, 
                         files_text=self.log(4, L2("gathering config content")))
      self.DATA['variables'].append('cvars[\'config-release\']')

    # kickstart 
    self.ksxpath = 'kickstart'
    if self.config.get('kickstart', False): # test ks provided
      KickstartEventMixin.setup(self)
    elif 'ks-path' in self.cvars:
      self.kstext = self.cvars['kickstart-file'].read_text() # production ks provided
    else:
      self.kstext = ''


  def run(self):
    # sync files from compose (os-dir) folder
    self.SOFTWARE_STORE.rm(force=True)
    self.io.process_files(link=True, text="preparing test system repository", 
                          what='os-dir')

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
    self.log(0, L1('publishing to %s' % self.localpath))
    self.localpath.rm(force=True)
    self.link(self.SOFTWARE_STORE, self.localpath) 
    self.chcon(self.localpath)

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['test-webpath'] = self.webpath
    self.cvars['test-kstext'] = self.kstext # provided by kickstart mixin
    self.cvars['test-repomdfile'] = self.repomdfile # provided by repomdmixin

