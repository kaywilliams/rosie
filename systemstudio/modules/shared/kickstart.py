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

from systemstudio.errors import SystemStudioError

class KickstartEventMixin:
  ksxpath = '.'
  ksname = 'ks.cfg'

  def setup(self):
    self.ksfile = self.SOFTWARE_STORE/self.ksname

    # read the text or file specified in the kickstart element
    # note: we download the existing file here rather than use add_fpath as
    # the file is small and processing is cleaner 
    elem = self.config.get(self.ksxpath)
    self.ks_source = '' # track source for use in error messages
    if elem.get('@content', 'file') == 'text':
      self.kstext = (elem.text or '')
      self.kssource = ('<kickstart content="text">\n  %s\n</kickstart>' %
                      ('\n  ').join([ l.strip() for l in self.kstext.split('\n')]))
    else:
      self.io.validate_input_file(elem.text, self._configtree.getpath(elem))
      self.kstext = self.io.abspath(elem.text).read_text().strip()
      self.kssource = 'kickstart file: %s' % self.io.abspath(elem.text)

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

class KickstartValidationError(SystemStudioError):
  message = ( "%(message)s" ) 
