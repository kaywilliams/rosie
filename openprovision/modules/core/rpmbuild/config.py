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
from StringIO import StringIO

from openprovision.util import pps

from openprovision.event        import Event
from openprovision.event.fileio import MissingXpathInputFileError

from openprovision.validate     import InvalidConfigError

from openprovision.errors         import assert_file_readable

from openprovision.modules.shared.config import ConfigEventMixin

import cPickle
import hashlib
import yum

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ConfigEvent'],
  description = 'creates a configuration RPM',
  group       = 'rpmbuild',
)

class ConfigEvent(ConfigEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'config',
      parentid = 'rpmbuild',
      version = '1.25',
      provides = ['rpmbuild-data', 'config-release', 'gpgkeys', 
                  'gpgcheck-enabled', 'os-content'],
      requires = ['input-repos', 'pubkey', 'web-path'],
    )

    ConfigEventMixin.__init__(self) 

    self.DATA = {
      'variables': ['name', 'fullname', 'systemid', 'rpm.release',
                    'cvars[\'web-path\']'],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }
  def setup(self):
    ConfigEventMixin.setup(self, webpath=self.cvars['web-path']/'os')

  def apply(self):
    self.rpm._apply()

    self.cvars['config-release'] = (self.cvars['rpmbuild-data']['config']
                                              ['rpm-release'])

    if self.pklfile.exists():
      fo = self.pklfile.open('rb')
      self.cvars['gpgkeys']=cPickle.load(fo)
      fo.close()
    else:
      self.cvars['gpgkeys']=[]

