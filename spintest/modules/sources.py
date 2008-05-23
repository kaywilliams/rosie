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

from rendition.xmllib import config

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_extension_suite

class SourceEventTestCase(EventTestCase):
  moduleid = 'sources'

  def _make_default_config(self):
    top = EventTestCase._make_default_config(self)

    src = self._make_source_repos_config()
    if src: top.append(src)

    return top

  def _make_source_repos_config(self):
    repos = config.Element('sources', attrs={'enabled': 'true'})

    if self.distro == 'redhat' and self.version == '5Server':
      repo = config.Element('repo', attrs={'id': 'base-source'}, parent=repos)
      config.Element('baseurl', parent=repo,
        text='http://www.renditionsoftware.com/mirrors/redhat/'
             'enterprise/5Server/en/os/SRPMS/')

    else:

      for repoid in ['base-source']:
        repo = config.Element('repo', attrs={'id': repoid}, parent=repos)
        config.Element('mirrorlist', parent=repo)
        config.Element('gpgkey', parent=repo)
        config.Element('gpgcheck', text='no', parent=repo)

      for repoid in ['everything-source', 'updates-source']:
        # disable each repo
        repo = config.Element('repo', attrs={'id': repoid}, parent=repos)
        config.Element('enabled', text='no', parent=repo)

    return repos



class SourceReposEventTestCase(SourceEventTestCase):
  eventid  = 'source-repos'

class Test_NoBase(SourceReposEventTestCase):
  "without base-info and repos sections, raises RuntimeError"
  _conf = ["<base/>","<source enabled='true'/>"]

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(RuntimeError, self.event)


class SourcesEventTestCase(SourceEventTestCase):
  eventid  = 'sources'

def make_suite(distro, version, arch):
  suite = ModuleTestSuite('sources')

  # disabling source test cases until Uday deals with the no repodata situation
  suite.addTest(make_extension_suite(SourceReposEventTestCase, distro, version, arch))
  suite.addTest(Test_NoBase(distro, version, arch))
  suite.addTest(make_extension_suite(SourcesEventTestCase, distro, version, arch))

  return suite
