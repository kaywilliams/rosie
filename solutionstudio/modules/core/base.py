#
# Copyright (c) 2010
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
"""
base.py

provides information about the base distribution
"""
from solutionstudio.util import FormattedFile as ffile
from solutionstudio.util import img
from solutionstudio.util import repo
from solutionstudio.util import versort

from solutionstudio.errors  import assert_file_has_content
from solutionstudio.event   import Event
from solutionstudio.logging import L1

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['BaseInfoEvent'],
  description = 'reads the .buildstamp file from the base distribution',
)

class BaseInfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'base-info',
      parentid = 'setup',
      requires = ['anaconda-version', 'installer-repo'],
      provides = ['base-info'],
    )

    self.DATA = {
      'input':     [],
      'output':    [],
      'variables': ['cvars[\'anaconda-version\']'],
    }

  def error(self, e):
    Event.error(self, e)
    try:
      self.image.close()
    except:
      pass

  def setup(self):
    self.diff.setup(self.DATA)

    initrd_in=( self.cvars['installer-repo'].url /
                self.locals.L_FILES['isolinux']['initrd.img']['path'] )

    self.io.add_fpath(initrd_in, self.mddir, id='initrd.img')
    self.initrd_out = self.io.list_output(what='initrd.img')[0]
    self.buildstamp_out = self.mddir/'.buildstamp'
    self.DATA['output'].append(self.buildstamp_out)

  def run(self):
    self.log(2, L1("reading buildstamp file from base repository"))

    # download initrd.img
    self.io.sync_input(cache=True, callback=Event.link_callback,
                       text=None, what='initrd.img')

    # extract buildstamp
    image = self.locals.L_FILES['isolinux']['initrd.img']
    self.image = img.MakeImage(self.initrd_out, image['format'], image.get('zipped', False))
    self.image.open('r')
    self.image.read('.buildstamp', self.mddir)
    self.image.close()
    img.cleanup()

  def apply(self):
    self.io.clean_eventcache()

    # parse buildstamp
    buildstamp = ffile.DictToFormattedFile(self.locals.L_BUILDSTAMP_FORMAT)

    # update base vars
    assert_file_has_content(self.buildstamp_out)
    self.cvars.setdefault('base-info', {}).update(buildstamp.read(self.buildstamp_out))

  def verify_buildstamp_file(self):
    "verify buildstamp file exists"
    self.verifier.failUnlessExists(self.buildstamp_out)
  def verify_cvars(self):
    "verify cvars exist"
    self.verifier.failUnlessSet('base-info')
