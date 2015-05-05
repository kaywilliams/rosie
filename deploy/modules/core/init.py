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
from deploy.event   import Event, CLASS_META
from deploy.dlogging import L1

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['InitEvent', 'SetupEvents', 'OSEvents',
                   'TestEvents', 'PublishEvents'],
    description = 'creates temporary and cache folders',
  )

class InitEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'init',
      parentid = 'all',
      ptr = ptr,
      provides = ['option-parser'],
      suppress_run_message = True
    )

  def clean(self):
    if self.METADATA_DIR.exists():
      self.log(2, L1("cleaning '%s'" % self.METADATA_DIR))
      self.METADATA_DIR.rm(recursive=True)

  def apply(self):
    for folder in [self.METADATA_DIR]:
      if not folder.exists():
        self.log(4, L1("making directory '%s'" % folder))
        folder.mkdirs()
      folder.chown(0,0)
      folder.chmod(0700)

  def verify_directories_exist(self):
    "output directories exist"
    for folder in [self.METADATA_DIR]:
      self.verifier.failUnless(folder.exists(), "folder '%s' does not exist" % folder)

class SetupEvents(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'setup-events',
      parentid = 'all',
      ptr = ptr,
      properties = CLASS_META,
      comes_after = ['init'],
      conditionally_comes_after = ['autoclean'],
      suppress_run_message = True
    )

    if self.type == 'build':
      self.enabled = False

class OSEvents(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'os-events',
      parentid = 'all',
      ptr = ptr,
      properties = CLASS_META,
      provides = ['os-events'],
      comes_after = ['setup-events'],
      suppress_run_message = True
    )

    if self.type == 'build':
      self.enabled = False

class TestEvents(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'test-events',
      parentid = 'all',
      ptr = ptr,
      properties = CLASS_META,
      comes_after = [ 'os-events' ],
      suppress_run_message = True
    )

    if self.type == 'build':
      self.enabled = False

class PublishEvents(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'publish-events',
      parentid = 'all',
      ptr = ptr,
      properties = CLASS_META,
      conditionally_comes_after = [ 'os-events', 'test-events' ],
      suppress_run_message = True
    )

    if self.type == 'build':
      self.enabled = False
