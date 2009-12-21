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
import copy

from rendition import repo
from rendition.rxml import config

from sbtest        import EventTestCase, ModuleTestSuite
from sbtest.core   import make_extension_suite

class SourceEventTestCase(EventTestCase):
  moduleid = 'sources'

  def _make_default_config(self):
    top = EventTestCase._make_default_config(self)

    src = self._make_source_repos_config()
    if src is not None: top.append(src)

    return top

  def _make_source_repos_config(self):
    repos = config.Element('sources', attrs={'enabled': 'true'})

    r = repo.getDefaultRepoById('base-source', distro=self.distro,
                                               version=self.version,
                                               arch=self.arch,
                                               include_baseurl=True,
                                               baseurl='http://www.renditionsoftware.com/mirrors/%s' % self.distro)
    r.update({'mirrorlist': None, 'gpgkey': None, 'gpgcheck': 'no'})

    repos.append(r.toxml())

    return repos



class SourceReposEventTestCase(SourceEventTestCase):
  eventid  = 'source-repos'


class SourcesEventTestCase(SourceEventTestCase):
  eventid  = 'sources'

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('sources')

  # source-repos
  suite.addTest(make_extension_suite(SourceReposEventTestCase, distro, version, arch))

  # sources
  suite.addTest(make_extension_suite(SourcesEventTestCase, distro, version, arch))

  return suite
