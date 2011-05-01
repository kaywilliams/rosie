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

import rpm

from systemstudio.util   import pps
from systemstudio.util   import shlib
from systemstudio.errors import SystemStudioError

from systemstudio.util.versort import Version

from systemstudio.event import Event

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['KickstartEvent'],
  description = 'downloads a default kickstart file',
  group       = 'installer',
)

class KickstartEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'kickstart',
      parentid = 'installer',
      version = 1.01,
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content'],
    )

    self.DATA = {
      'config':    ['.'],
      'variables': [],
      'output':    [],
    }

    # get pykickstart version
    ts = rpm.TransactionSet()
    h = list(ts.dbMatch('name', 'pykickstart'))[0]
    self.cvars['pykickstart-version'] = Version("%s-%s" % (h['version'], 
                                                           h['release']))

  def setup(self):
    self.diff.setup(self.DATA)

    self.ksname = 'ks.cfg'
    self.ksfile = self.SOFTWARE_STORE/self.ksname

    # read the text or file specified in the kickstart element
    # note: we download the existing file here rather than use add_fpath as
    # the file is small and processing is cleaner 
    elem = self.config.get('.')
    if elem.get('@content', 'file') == 'text':
      self.kstext = (elem.text or '')
    else:
      self.io.validate_input_file(elem.text, elem) 
      self.kstext = self.io.abspath(elem.text).read_text().strip()

    self.DATA['variables'].append('kstext')

  def run(self):

    ksver = 'rhel%s' %  self.cvars['base-info']['version'].split('.')[0]

    adds=[{'test'    : "line.startswith('#version')",
           'text'    : "\n#version %s" % ksver },
          {'test'    :  "line.startswith('%packages')",
           'text'    : "\n%packages\ngroup core\n%end",},]

    # test for missing ks parameters
    for line in self.kstext.split('\n'): 
      for item in adds:
        if eval(item['test']):
          item['exists'] = True

    # add missing parameters
    for item in adds:
      if not 'exists' in item: #add to end for sensible line no's in validation
        self.kstext = self.kstext + item['text']

    # write kickstart
    self.ksfile.dirname.mkdirs()
    self.ksfile.write_text(self.kstext + '\n')

    #validate kickstart
    map = { 'ksver': ksver, 'ksfile': self.ksfile }
    exec(self.locals.L_PYKICKSTART % map)

    self.DATA['output'].append(self.ksfile)

  def apply(self):
    self.cvars['kickstart-file'] = self.ksfile
    self.cvars['ks-path'] = pps.path('/%s' % self.cvars['kickstart-file'].basename)

  def verify_cvars(self):
    "kickstart file exists"
    self.verifier.failUnlessExists(self.cvars['kickstart-file'])

class KickstartValidationError(SystemStudioError):
  message = ( "%(message)s" )
