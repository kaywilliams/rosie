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
from openprovision.util import difftest

# add support for serialization of versort classes
from openprovision.util.versort.serialize import VersionXmlSerializer
difftest.rxml.serialize.SERIALIZERS.insert(0, VersionXmlSerializer())

class DiffMixin:
  def __init__(self):
    self.diff = DiffObject(self)

  def clean(self):
    self.diff.clean_metadata()

  def check(self):
    return self.diff.test_diffs()

  def postrun(self):
    self.diff.write_metadata()


class DiffObject:
  "Dummy object to contain diff-related functions"
  def __init__(self, ptr):
    self.ptr = ptr
    self.tester = difftest.DiffTest(self.ptr.mdfile)
    self.handlers = {}

    self.config = None
    self.output = None
    self.input = None
    self.variables = None

  # former DiffMixin stuff
  def setup(self, data):
    if data.has_key('input') and not self.input:
      self.add_handler(difftest.InputHandler(data['input']))
    if data.has_key('output') and not self.output:
      self.add_handler(difftest.OutputHandler(data['output']))
    if data.has_key('variables') and not self.variables:
      self.add_handler(difftest.VariablesHandler(data['variables'], self.ptr))
    if data.has_key('config') and not self.config:
      self.add_handler(difftest.ConfigHandler(data['config'], self.ptr.config))

  def add_handler(self, handler):
    self.tester.addHandler(handler)
    self.handlers[handler.name] = handler
    setattr(self, handler.name, handler)

  def clean_metadata(self):  self.tester.clean_metadata()
  def read_metadata(self):   self.tester.read_metadata()
  def write_metadata(self):  self.tester.write_metadata()

  def test_diffs(self, debug=None):
    # if we don't use difftest for stuff, just return True
    if not self.handlers: return True

    old_dbgval = self.tester.debug
    if debug is not None:
      self.tester.debug = debug

    self.read_metadata()

    for handler in self.handlers.values():
      handler.diff()

    self.tester.debug = old_dbgval

    for handler in self.handlers.values():
      if handler.difference(): return True
    return False
