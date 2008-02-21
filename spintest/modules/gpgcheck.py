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
from spintest      import EventTestCase, ModuleTestSuite, config
from spintest.core import make_core_suite

def _make_conf(basedistro='fedora-6', keys=True):
  if keys:
    repo = config._make_repo('%s-base' % basedistro, enabled='1', gpgcheck='1')
  else:
    repo = config._make_repo('%s-base' % basedistro, enabled='1', gpgcheck='1', gpgkey='')

  # hack, shouldn't have to convert back to string
  return str(config.make_repos(basedistro, [repo]))

class GpgcheckEventTestCase(EventTestCase):
  moduleid = 'gpgcheck'
  eventid  = 'gpgcheck'
  def __init__(self, basedistro, arch, conf=None):
    self._conf = _make_conf(basedistro)
    EventTestCase.__init__(self, basedistro, arch, conf)

class Test_GpgKeysNotProvided(GpgcheckEventTestCase):
  "raises RuntimeError when no keys are provided"
  def __init__(self, basedistro, arch, conf=None):
    self._conf = _make_conf(basedistro, keys=False)
    EventTestCase.__init__(self, basedistro, arch, conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('gpgcheck')

  suite.addTest(make_core_suite(GpgcheckEventTestCase, basedistro, arch))
  suite.addTest(Test_GpgKeysNotProvided(basedistro, arch))

  return suite
