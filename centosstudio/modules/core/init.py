#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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
from centosstudio.event   import Event, CLASS_META
from centosstudio.cslogging import L1

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['InitEvent', 'SetupEvents', 'OSEvents', 
                 'TestEvents', 'PublishEvents'],
  description = 'creates temporary and cache folders',
)

class InitEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'init',
      parentid = 'all',
      provides = ['option-parser'],
      suppress_run_message = True
    )

  def clean(self):
    if self.METADATA_DIR.exists():
      self.log(2, L1("cleaning '%s'" % self.METADATA_DIR))
      self.METADATA_DIR.rm(recursive=True)

  def apply(self):
    for folder in [self.TEMP_DIR, self.METADATA_DIR]:
      if not folder.exists():
        self.log(4, L1("making directory '%s'" % folder))
        folder.mkdirs()

  def verify_directories_exist(self):
    "output directories exist"
    for folder in [self.TEMP_DIR, self.METADATA_DIR]:
      self.verifier.failUnless(folder.exists(), "folder '%s' does not exist" % folder)

class SetupEvents(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'setup-events',
      parentid = 'all',
      properties = CLASS_META,
      comes_after = ['init'],
      conditionally_comes_after = ['autoclean'],
      suppress_run_message = True
    )

class OSEvents(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'os-events',
      parentid = 'all',
      properties = CLASS_META,
      comes_after = ['setup-events'],
      suppress_run_message = True
    )

class TestEvents(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'test-events',
      parentid = 'all',
      properties = CLASS_META,
      comes_before = [ 'publish-events' ],
      suppress_run_message = True
    )

class PublishEvents(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish-events',
      parentid = 'all',
      properties = CLASS_META,
      comes_after = [ 'os-events', 'test-events' ],
      suppress_run_message = True
    )
