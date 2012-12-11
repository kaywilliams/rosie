#
# Copyright (c) 2012
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

from deploy.event import Event

from deploy.modules.shared import ExecuteEventMixin

from deploy.util import pps

class InputEventMixin(ExecuteEventMixin, Event):
  input_mixin_version = "1.00"

  def setup(self):
    self.input_dir = self.mddir / 'input'
    self.input_dir.mkdirs()
    self.DATA.setdefault('variables', []).extend(['input_mixin_version',
                                                  'input_dir'])
    self.DATA.setdefault('config', []).append('input-script')

    # resolve macros
    self.config.resolve_macros('.', {'%{input-dir}': self.input_dir})


    input_scripts = self.config.xpath('input-script', [])
    tmpfile = self.mddir / 'input_script.tmp'
    for s in input_scripts:
      text = s.getxpath('text()')
      if text is not None: 
        tmpfile.write_text(text  + '\n')
        tmpfile.chmod(0700)
        self._local_execute(tmpfile, s.getbool('@verbose', False))

    if self.input_dir.findpaths(type=pps.constants.TYPE_FILE):
      self.DATA.setdefault('input', []).append(self.input_dir)

  def run(self):
    self.DATA.setdefault('output', []).append(self.input_dir)
