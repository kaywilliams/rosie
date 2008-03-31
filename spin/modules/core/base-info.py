#
# Copyright (c) 2007, 2008
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
base-info.py

provides information about the base distribution
"""
from rendition import FormattedFile as ffile
from rendition import img

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event
from spin.logging   import L1

API_VERSION = 5.0
EVENTS = {'setup': ['BaseInfoEvent']}

class BaseInfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'base-info',
      provides = ['base-info'],
      requires = ['anaconda-version', 'base-repoid'],
    )

    self.DATA =  {
      'input':     [],
      'output':    [],
    }

  def error(self, e):
    Event.error(self, e)
    try:
      self.image.close()
    except:
      pass

  def setup(self):
    self.diff.setup(self.DATA)

    initrd_in=( self.cvars['repos'][self.cvars['base-repoid']].osdir /
                self.locals.L_FILES['isolinux']['initrd.img']['path'] )

    self.io.add_fpath(initrd_in, self.mddir, id='initrd.img')
    self.initrd_out = self.io.list_output(what='initrd.img')[0]
    self.buildstamp_out = self.mddir/'.buildstamp'
    self.DATA['output'].append(self.buildstamp_out)

  def run(self):
    self.log(2, L1("reading buildstamp file from base repository"))

    # download initrd.img
    self.io.sync_input(cache=True, callback=Event.link_callback, text=None)

    # extract buildstamp
    image = self.locals.L_FILES['isolinux']['initrd.img']
    self.image = img.MakeImage(self.initrd_out, image['format'], image.get('zipped', False))
    self.image.open('r')
    self.image.read('.buildstamp', self.mddir)
    self.image.close()
    img.cleanup()

    # update metadata
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    # parse buildstamp
    buildstamp = ffile.DictToFormattedFile(self.locals.L_BUILDSTAMP_FORMAT)
    # update base vars
    try:
      self.cvars['base-info'] = buildstamp.read(self.buildstamp_out)
    except:
      pass # caught by verification

  def verify_buildstamp_file(self):
    "verify buildstamp file exists"
    self.verifier.failUnlessExists(self.buildstamp_out)
  def verify_base_vars(self):
    "verify base-info cvar"
    self.verifier.failUnless(self.cvars['base-info'])
