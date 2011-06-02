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
import subprocess as sub

from libvirt import libvirtError

from systemstudio.callback  import BuildDepsolveCallback
from systemstudio.event     import Event, CLASS_META
from systemstudio.sslogging import L1, L2, L3
from systemstudio.util      import pps

from systemstudio.modules.shared import RepomdMixin
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
                PublishEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test',
      parentid = 'all',
      requires = ['os-dir', 'config-release'], 
      conditionally_requires = ['kickstart-file'] 
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
    KickstartEventMixin.setup(self)

    # script
    self.io.add_xpath('script', self.mddir, id='script', mode='750')

    # track changes to base installer files (but not product.img, updates.img)
    self.installer_files = []
    for key in [ x for x in self.locals.L_FILES if x != 'installer' ]:
      for file in self.locals.L_FILES[key]:
        self.installer_files.append(self.cvars['installer-repo'].url /
          self.locals.L_FILES[key][file]['path'] % 
            self.cvars['distribution-info'])
    self.DATA['input'].extend(self.installer_files)

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
    (self.SOFTWARE_STORE/'ks.cfg').rm(force=True)
    KickstartEventMixin.run(self) 

    # publish to test folder
    self.log(0, L1('publishing to %s' % self.pubpath))
    self.pubpath.rm(force=True)
    self.link(self.SOFTWARE_STORE, self.pubpath) 
    self.chcon(self.pubpath)

    # get script
    self.script = self.io.process_files(text=None, what='script')[0]

    # update 
    if not self._rebuild() and self._activate():
      self.log(1, L1("running update script"))
      r = self._update()
      if r != 0: sys.exit(1)

    # install
    else:
      self.log(1, L1("running install script"))
      self._clean()
      self._install()

    # test
    # self.log(1, L1("running test script"))

  def apply(self):
    self.io.clean_eventcache()


  ##### Helper Functions #####

  def _rebuild(self):
    '''Test current rebuild triggers against prior and return true if changes'''

    # did install script change (either file or text)?
    '''
    script_file = self.io.list_input(what='install-script')
    if (( script_file and script_file[0] in self.diff.input.diffdict) 
         or '/distribution/test/install-script' in self.diff.config.diffdict):
      return True
    '''
  
    # did kickstart change?
    if 'kstext' in self.diff.variables.diffdict: 
      return True

    # did installer files change?
    for f in self.installer_files:
      if f in self.diff.input.diffdict:
        return True
      
    # if not, install parameters haven't changed, no need to rebuild
    return False 

  def _clean(self):
    self.log(2, L2("cleaning machine"))
    r = sub.call('%s clean %s' % (self.script, self.distributionid), shell=True)
    if r != 0:
      raise Exception("make me a systemstudio error")
 
  def _activate(self):
    r = sub.call('%s activate %s' % (self.script, self.distributionid), shell=True)
    if r != 0:
      raise Exception("make me a systemstudio error")
  
  def _install(self):
    self.log(2, L2("installing machine"))
    r = sub.call('%s install %s %s' % (self.script, 
                 self.distributionid, self.webpath), shell=True) 
    if r != 0:
      raise Exception("make me a systemstudio error")
  
  def _update(self):
    self.log(2, L2("updating machine"))
    r = sub.call('%s update %s' % (self.script, self.distributionid),
                                   shell=True)
    if r != 0:
      raise Exception("make me a systemstudio error")

