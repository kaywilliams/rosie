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
from systemstudio.util import pps

from sstest      import EventTestCase, ModuleTestSuite
from sstest.core import make_extension_suite

class GpgsignTestCase(EventTestCase):
  moduleid = 'gpgsign'
  eventid  = 'gpgsign'
  _conf = """<gpgsign>
    <public-key>%s</public-key>
    <secret-key>%s</secret-key>
    <passphrase></passphrase>
  </gpgsign>""" % (pps.path(__file__).abspath().dirname/'RPM-GPG-KEY-test',
                   pps.path(__file__).abspath().dirname/'RPM-GPG-SEC-KEY-test')

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('gpgsign')

  suite.addTest(make_extension_suite(GpgsignTestCase, distro, version, arch))

  return suite
