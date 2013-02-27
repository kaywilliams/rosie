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
"""
infofiles.py

generates system information files: .discinfo, .treeinfo, and .buildstamp
"""

import copy
import time

from deploy.util import FormattedFile as ffile

from deploy.event  import Event
from deploy.locals import sort_keys

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['DiscinfoEvent', 'TreeinfoEvent', 'BuildstampEvent'],
    description = 'creates .buildstamp, .treeinfo, and .discinfo files',
    group       = 'installer',
  )

class DiscinfoEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'discinfo',
      version = '1.01',
      parentid = 'installer',
      ptr = ptr,
      provides = ['.discinfo', 'os-content'],
      requires = ['anaconda-version'],
    )

    self.difile = self.OUTPUT_DIR/'.discinfo'

    self.DATA =  {
      'variables': ['fullname', 'arch', 'packagepath', 'difile',
                    'cvars[\'anaconda-version\']'],
      'output':    [self.difile]
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    # create empty .discinfo formatted file object
    discinfo = ffile.DictToFormattedFile(self.locals.L_DISCINFO_FORMAT)

    # get name, fullname, and arch from cvars
    app_vars = copy.deepcopy(self.cvars['distribution-info'])

    # add timestamp and discs using defaults to match anaconda makestamp.py
    app_vars.update({'timestamp': str(time.time()), 'discs': 'ALL'})

    # write .discinfo
    self.difile.dirname.mkdirs()
    discinfo.write(self.difile, **app_vars)
    self.difile.chmod(0644)
    self.DATA['output'].append(self.difile)

  def verify_discinfo_file_exists(self):
    ".discinfo file exists"
    self.verifier.failUnlessExists(self.difile)


class TreeinfoEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'treeinfo',
      version = '1.02',
      parentid = 'installer',
      ptr = ptr,
      provides = ['treeinfo-text', 'os-content'],
      requires = ['anaconda-version', 'treeinfo-checksums'],
    )

    self.tifile = self.OUTPUT_DIR/'.treeinfo'

    self.DATA =  {
      'variables': ['name', 'version', 'packagepath', 'arch', 'tifile'],
      'output':    [self.tifile],
    }

  def setup(self):
    inputs = []
    for (software_store, file) in self.cvars.get('treeinfo-checksums', []):
      inputs.append(software_store / file)
    self.DATA['input'] = inputs
    self.diff.setup(self.DATA)

  def run(self):
    lines = []

    # add timestamp to base vars (doesn't have to match .discinfo's timestamp)
    vars = copy.deepcopy(self.cvars['distribution-info'])
    vars.update({'timestamp': str(time.time()),
                 'family':    self.cvars['base-treeinfo'].get(
                              'general', 'family')})

    # generate .treeinfo lines
    for section in sort_keys(self.locals.L_TREEINFO_FORMAT):
      lines.append('[%s]' % section % vars)
      content = self.locals.L_TREEINFO_FORMAT[section]['content']
      for item in sort_keys(content):
        lines.append('%s = %s' % (item % vars, content[item]['value'] % vars))
      lines.append('')

    # compute checksums
    if 'treeinfo-checksums' in self.cvars:
      lines.append('[checksums]')
      checksums = sorted(self.cvars['treeinfo-checksums'])
      for software_store, file in checksums:
        shasum = (software_store / file).checksum(type="sha1")
        lines.append('%s = sha1:%s' % (file, shasum))

    # write .treeinfo
    self.tifile.dirname.mkdirs()
    if not self.tifile.exists():
      self.tifile.touch()
    self.tifile.write_lines(lines)
    self.tifile.chmod(0644)

  def apply(self):
    if self.tifile.exists():
      self.cvars['treeinfo-text'] = self.tifile.read_text().strip()

  def verify_treeinfo_file_exists(self):
    ".treeinfo file exists"
    self.verifier.failUnlessExists(self.tifile)


class BuildstampEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'buildstamp',
      version = '1',
      parentid = 'installer',
      ptr = ptr,
      provides = ['buildstamp-file'],
      requires = ['anaconda-version', 'base-info'],
    )

    self.bsfile = self.mddir/'.buildstamp'

    self.DATA = {
      'variables': ['fullname', 'version', 'packagepath', 'arch', 'webloc',
                    'cvars[\'anaconda-version\']',
                    'cvars[\'base-info\']'],
      'output':    [self.bsfile],
    }

  def setup(self):
    self.diff.setup(self.DATA)

  def run(self):
    "Generate a .buildstamp file."

    buildstamp = ffile.DictToFormattedFile(self.locals.L_BUILDSTAMP_FORMAT)

    app_vars = copy.deepcopy(self.cvars['base-info'])
    app_vars.update(self.cvars['distribution-info'])

    self.bsfile.dirname.mkdirs()
    buildstamp.write(self.bsfile, **app_vars)
    self.bsfile.chmod(0644)

  def apply(self):
    self.cvars['buildstamp-file'] = self.bsfile

  def verify_buildstamp_file_exists(self):
    ".buildstamp file exists"
    self.verifier.failUnlessExists(self.bsfile)
