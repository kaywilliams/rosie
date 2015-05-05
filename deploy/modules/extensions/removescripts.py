# Experimental Module - Not recommended for current use

#
# Copyright (c) 2015
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
from deploy.util import rxml

from deploy.util.difftest.handlers import DiffHandler

from deploy.event   import Event
from deploy.dlogging import L1, L2

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['RemoveScriptEvent'],
    description = 'creates a script for removing a Deploy build',
  )

class RemoveScriptEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'remove-script',
      parentid = 'setup-events',
      provides = ['remove-dir'],
      suppress_run_message = True,
      ptr = ptr,
    )

  def setup(self):
    self.remove_script = self.DATA_DIR / 'remove.sh'
    self.remove_dir = self.DATA_DIR / 'remove'

    # script text
    text = """for f in `/usr/bin/find %s -type f`; do
  /bin/chmod +x $f
  $f
done
""" % self.remove_dir

    # write script
    self.remove_script.write_text(text)
    self.remove_script.chmod(0750)

    # clean script dir
    self.remove_dir.rm(recursive=True, force=True)
    self.remove_dir.mkdirs()

    # remove cache dir script
    (self.remove_dir / 'remove_cache_dir').write_text("""if [ -d %s ] ; then
  /bin/rm -rf %s
fi""" % (self.METADATA_DIR, self.METADATA_DIR))

  def apply(self):
    self.cvars['remove-dir'] = self.remove_dir
