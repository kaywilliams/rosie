#
# Copyright (c) 2011
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

from systemstudio.callback  import BuildDepsolveCallback
from systemstudio.event     import Event, CLASS_META
from systemstudio.sslogging import L1, L2, L3
from systemstudio.util      import pps

from systemstudio.modules.shared import RepomdMixin, DeployEventMixin
from systemstudio.modules.shared.config import ConfigEventMixin
from systemstudio.modules.shared.kickstart import KickstartEventMixin
from systemstudio.modules.shared.publish import PublishEventMixin

P = pps.path

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['TestEvent'],
  description = 'tests distribution installation and update',
)


class TestEvent(ConfigEventMixin, RepomdMixin, KickstartEventMixin, 
                PublishEventMixin, DeployEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test',
      parentid = 'all',
      requires = ['os-dir', 'config-release'], 
    )

    self.configxpath = 'config'
    ConfigEventMixin.__init__(self)
    RepomdMixin.__init__(self)

    self.pubpath = self.get_local('local-dir', 
                                  '/var/www/html/distributions/test')
    self.webpath = self.get_remote('remote-url', 'distributions/test')

    self.DATA =  {
      'config':    ['.'],
      'input':     [],
      'output':    [],
      'variables': ['cvars[\'config-release\']', 'pubpath', 'webpath'],
    }

  def validate(self):
    ConfigEventMixin.validate(self)

  def clean(self):
    Event.clean(self)
    self.pubpath.rm(recursive=True, force=True) #publish path

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
    ConfigEventMixin.setup(self, webpath=self.webpath, 
                         release=self.cvars['config-release'] + '.test',
                         files_cb=self.link_callback, 
                         files_text=self.log(4, L2("gathering config content")))

    # kickstart 
    self.ksxpath = 'kickstart'
    if self.config.get('kickstart', None) is not None:
      KickstartEventMixin.setup(self)

    # deploy
    DeployEventMixin.setup(self)

  def run(self):
    # sync files from compose (os-dir) folder
    self.SOFTWARE_STORE.rm(force=True)
    self.io.process_files(link=True, text="preparing test distribution", 
                          what='os-dir')

    # modify config-rpm
    ConfigEventMixin.run(self)
    (self.rpm.rpm_path).cp(self.SOFTWARE_STORE/'Packages')
    self.DATA['output'].append(self.SOFTWARE_STORE/'Packages'/
                               self.rpm.rpm_path.basename)

    # update repodata
    self.createrepo(self.SOFTWARE_STORE, 
                    groupfile=self.cvars['groupfile'],
                    checksum=self.locals.L_CHECKSUM['type'])

    # update kickstart
    if self.config.get('kickstart', None) is not None:
      (self.SOFTWARE_STORE/'ks.cfg').rm(force=True)
      KickstartEventMixin.run(self) 

    # publish to test folder
    self.log(0, L1('publishing to %s' % self.pubpath))
    self.pubpath.rm(force=True)
    self.link(self.SOFTWARE_STORE, self.pubpath) 
    self.chcon(self.pubpath)

    # deploy
    DeployEventMixin.run(self)

  def apply(self):
    self.io.clean_eventcache()


