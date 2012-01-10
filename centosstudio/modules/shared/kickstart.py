#
# Copyright (c) 2012
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
import rpm

from centosstudio.errors import CentOSStudioError
from centosstudio.util.versort import Version

class KickstartEventMixin:
  kickstart_mixin_version = "1.02"

  def __init__(self):
    self.DATA['config'].append('kickstart')
    self.DATA['variables'].append('kickstart_mixin_version')

    self.ksxpath = '.'
    self.ksname = 'ks.cfg'

    # set pykickstart_version (used by locals mixin and cstest)
    ts = rpm.TransactionSet()
    h = list(ts.dbMatch('name', 'pykickstart'))[0]
    self.cvars['pykickstart-version'] = Version("%s-%s" % 
                                                (h['version'], h['release']))

  def setup(self):
    self.ksfile = self.SOFTWARE_STORE/self.ksname

    # read the text or file specified in the kickstart element
    elem = self.config.get(self.ksxpath)
    self.ks_source = '' # track source for use in error messages
    self.kstext = (elem.text or '')
    self.kssource = ('<kickstart>\n  %s\n</kickstart>' %
                    ('\n  ').join([ l.strip() for l in self.kstext.split('\n')]))

    self.DATA['variables'].append('kstext')

  def run(self):
    ksver = 'rhel%s' %  self.cvars['base-info']['version'].split('.')[0]

    # test for missing ks parameters
    adds = self.locals.L_KICKSTART_ADDS
    for line in self.kstext.split('\n'):
      for item in adds:
        if adds[item]['test']: adds[item]['exists'] = True

    # add missing parameters
    kstext = self.kstext[:] # self.kstext used for diff test, leave it alone
    for item in adds:
      if not 'exists' in item: #add to end for correct line no's in validation
        kstext = kstext + adds[item]['text']

    # write kickstart
    self.ksfile.dirname.mkdirs()
    self.ksfile.write_text(kstext + '\n')

    #validate kickstart
    map = { 'ksver': ksver, 'ksfile': self.ksfile }
    exec(self.locals.L_PYKICKSTART % map)

    self.DATA['output'].append(self.ksfile)

class KickstartValidationError(CentOSStudioError):
  message = ( "%(message)s" ) 
