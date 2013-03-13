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
import rpm

from deploy.errors import DeployEventError
from deploy.util.versort import Version

class KickstartEventMixin:
  kickstart_mixin_version = "1.02"

  def __init__(self, *args, **kwargs):
    if not hasattr(self, 'DATA'): self.DATA = {'config': [],
                                               'variables': [],
                                               'output': []}
    self.DATA['config'].append('kickstart')
    self.DATA['variables'].append('kickstart_mixin_version')

    self.provides.update([ 
      'ksname', 
          # global default basename (i.e. ks.cfg). Used by modules that
          # look for a kickstart # on a remote web server (e.g. deploy), or
          # within an image (e.g. initrd-image), etc.
      '%s-ksfile' % self.moduleid, 
          # path to created file in event cache or None
      ])

    # set pykickstart_version (used by locals mixin and dtest)
    ts = rpm.TransactionSet()
    h = list(ts.dbMatch('name', 'pykickstart'))[0]
    self.cvars['pykickstart-version'] = Version("%s-%s" % 
                                                (h['version'], h['release']))

  def setup(self, default=''):
    self.diff.setup(self.DATA)

    # read the text or file specified in the kickstart element
    self.kstext = self.config.getxpath('kickstart/text()', default)
    if len(self.kstext) == 0:
      self.ksfile = None
      return

    self.ksname = 'ks.cfg'
    self.ksfile = self.OUTPUT_DIR / self.ksname
    self.DATA['variables'].extend(['ksname'])

    self.ks_source = '' # track source for use in error messages
    self.kssource = ('<kickstart>\n  %s\n</kickstart>' %
                    ('\n  ').join([ l.strip() 
                    for l in self.kstext.split('\n')]))


  def run(self):
    if not self.ksfile: return

    ksver = 'rhel%s' %  self.version

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

  def apply(self):
    self.cvars['ksname'] = self.ksname #default kickstart filename (ks.cfg) 
    self.cvars['%s-ksfile' % self.moduleid ] = self.ksfile #path to file in 
                                                           #event cache or None

  def verify_kickstart_file(self):
    "kickstart file exists"
    if self.ksfile:
      self.verifier.failUnlessExists(self.cvars['%s-ksfile' % self.moduleid])

class KickstartValidationError(DeployEventError):
  message = ( "%(message)s" ) 
