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

class SourceReposEventTestCase(EventTestCase):
  moduleid = 'sources'
  eventid  = 'source-repos'
  def __init__(self, basedistro, arch, conf=None):
    self._conf = _make_source_repos(basedistro)
    EventTestCase.__init__(self, basedistro, arch, conf)

class SourcesEventTestCase(EventTestCase):
  moduleid = 'sources'
  eventid  = 'sources'
  def __init__(self, basedistro, arch, conf=None):
    self._conf = _make_source_repos(basedistro)
    EventTestCase.__init__(self, basedistro, arch, conf)

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('sources')

  suite.addTest(make_extension_suite(SourceReposEventTestCase, basedistro, arch))
  suite.addTest(make_extension_suite(SourcesEventTestCase, basedistro, arch))

  return suite

def _make_source_repos(distro):
  srcrepos = config.Element('sources')
  srcrepos.append(_make_repo('%s-base-source' % distro))
  return str(srcrepos) # hack, this has to be a string

def _make_repo(id, **kwargs):
  if id in SOURCE_REPOS.keys():
    d = copy.copy(SOURCE_REPOS[id]) # destructive
  else:
    d = {}

  d.update(kwargs)

  for k in ['baseurl']:
    if not d.has_key(k):
      raise ValueError("Missing key '%s' for repo '%s'" % (k, id))

  repo = config.Element('repo', attrs={'id': id})
  for k,v in d.items():
    config.Element(k, text=v, parent=repo)

  return repo

SOURCE_REPOS = {
  # fedora 6
  'fedora-6-base-source': {
    'name': 'fedora-6-base-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/core/6/source/SRPMS/'
  },
  'fedora-6-updates-source': {
    'name': 'fedora-6-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/core/updates/6/SRPMS/',
  },
  # fedora 7
  #'fedora-7-base-source': {
  #  'name': 'fedora-7-base-source',
  #  'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Fedora/source/SRPMS/',
  #},
  'fedora-7-base-source': {
    'name': 'fedora-7-base-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Everything/source/SRPMS/',
  },
  'fedora-7-updates-source': {
    'name': 'fedora-7-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/updates/7/SRPMS/',
  },
  # fedora 8
  #'fedora-8-base-source': {
  #  'name': 'fedora-8-base-source',
  #  'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Fedora/source/SRPMS/',
  #},
  'fedora-8-base-source': {
    'name': 'fedora-8-base-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Everything/source/SRPMS/',
  },
  'fedora-8-updates-source': {
    'name': 'fedora-8-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/updates/8/SRPMS/',
  },
  # redhat 5
  'redhat-5-base-source': {
    'name': 'redhat-5-base-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/redhat/linux/enterprise/5server/en/os/SRPMS/',
  },
  # centos 5
  'centos-5-base-source': {
    'name': 'centos-5-base-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/centos/5/os/SRPMS/',
  },
  'centos-5-updates-source': {
    'name': 'centos-5-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/centos/5/updates/SRPMS/',
  },
}
