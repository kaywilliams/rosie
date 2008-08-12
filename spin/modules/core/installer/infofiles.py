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
infofiles.py

generates distribution information files: .discinfo, .treeinfo, and .buildstamp
"""

import copy
import time

from rendition import FormattedFile as ffile

from spin.event  import Event
from spin.locals import sort_keys

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['DiscinfoEvent', 'TreeinfoEvent', 'BuildstampEvent'],
  description = 'creates .buildstamp, .treeinfo, and .discinfo files',
  group       = 'installer',
)

class DiscinfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'discinfo',
      version = '1',
      parentid = 'installer',
      provides = ['.discinfo'],
      requires = ['anaconda-version'],
    )

    self.difile = self.SOFTWARE_STORE/'.discinfo'

    self.DATA =  {
      'variables': ['fullname', 'basearch', 'packagepath',
                    'cvars[\'anaconda-version\']'],
      'output':    [self.difile]
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    # create empty .discinfo formatted file object
    discinfo = ffile.DictToFormattedFile(self.locals.L_DISCINFO_FORMAT)

    # get name, fullname, and basearch from cvars
    distro_vars = copy.deepcopy(self.cvars['distro-info'])

    # add timestamp and discs using defaults to match anaconda makestamp.py
    distro_vars.update({'timestamp': str(time.time()), 'discs': 'ALL'})

    # write .discinfo
    self.difile.dirname.mkdirs()
    discinfo.write(self.difile, **distro_vars)
    self.difile.chmod(0644)

  def apply(self):
    self.io.clean_eventcache()

  def verify_discinfo_file_exists(self):
    ".discinfo file exists"
    self.verifier.failUnlessExists(self.difile)


class TreeinfoEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'treeinfo',
      version = '1.1',
      parentid = 'installer',
      provides = ['.treeinfo'],
      requires = ['anaconda-version'],
    )

    self.tifile = self.SOFTWARE_STORE/'.treeinfo'

    self.DATA =  {
      'variables': ['name', 'version', 'packagepath', 'basearch'],
      'output':    [self.tifile]
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    lines = []

    # add timestamp to base vars (doesn't have to match .discinfo's timestamp)
    vars = copy.deepcopy(self.cvars['distro-info'])
    vars.update({'timestamp': str(time.time())})

    # generate .treeinfo lines
    for section in sort_keys(self.locals.L_TREEINFO_FORMAT):
      lines.append('[%s]' % section % vars)
      content = self.locals.L_TREEINFO_FORMAT[section]['content']
      for item in sort_keys(content):
        lines.append('%s = %s' % (item % vars, content[item]['value'] % vars))
      lines.append('')

    # write .treeinfo
    self.tifile.dirname.mkdirs()
    if not self.tifile.exists():
      self.tifile.touch()
    self.tifile.write_lines(lines)
    self.tifile.chmod(0644)

  def apply(self):
    self.io.clean_eventcache()

  def verify_treeinfo_file_exists(self):
    ".treeinfo file exists"
    self.verifier.failUnlessExists(self.tifile)


class BuildstampEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'buildstamp',
      version = '1',
      parentid = 'installer',
      provides = ['buildstamp-file'],
      requires = ['anaconda-version', 'base-info'],
    )

    self.bsfile = self.mddir/'.buildstamp'

    self.DATA = {
      'variables': ['fullname', 'version', 'name', 'basearch', 'webloc',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'base-info\']'],
      'output':    [self.bsfile],
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    "Generate a .buildstamp file."

    buildstamp = ffile.DictToFormattedFile(self.locals.L_BUILDSTAMP_FORMAT)

    distro_vars = copy.deepcopy(self.cvars['base-info'])
    distro_vars.update(self.cvars['distro-info'])

    self.bsfile.dirname.mkdirs()
    buildstamp.write(self.bsfile, **distro_vars)
    self.bsfile.chmod(0644)

  def apply(self):
    self.cvars['buildstamp-file'] = self.bsfile

  def verify_buildstamp_file_exists(self):
    ".buildstamp file exists"
    self.verifier.failUnlessExists(self.bsfile)
