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
from rendition import repo
from rendition import versort

from spin.event import Event, CLASS_META

from spin.modules.shared import RepoEventMixin

API_VERSION = 5.0

EVENTS = {'os': ['InstallerEvent'], 'setup': ['InstallerSetupEvent']}

class InstallerEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'installer',
      properties = CLASS_META,
      provides = ['os-content'],
      suppress_run_message = True,
    )

class InstallerSetupEvent(RepoEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'installer-setup',
      provides = [ 'installer-repo', 'anaconda-version-supplied'],
      conditionally_requires = [ 'base-distro' ],
      suppress_run_message = True,
    )

    self.DATA = {
      'variables': [],
      'config': ['.'],
    }

    RepoEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    addrepos = repo.RepoContainer()
    if self.config.pathexists('baseurl') or \
       self.config.pathexists('mirrorlist'):
      r = repo.IORepo(id='installer', name='installer')
      if self.config.pathexists('baseurl'): # not baseurl/text()
        r['baseurl'] = self.config.get('baseurl/text()', None)
      if self.config.pathexists('mirrorlist'): # not mirrorlist/text()
        r['mirrorlist'] = self.config.get('mirrorlist/text()', None)
      addrepos.add_repo(r)

    self.setup_repos('installer', cls=repo.IORepo, updates=addrepos)
    # don't call self.read_repodata() b/c installer repos don't necessarily
    # have repodata (and we don't use it regardless)

    self.anaconda_version = self.config.get('anaconda-version/text()', None)
    if self.anaconda_version is not None:
      self.anaconda_version = versort.Version(self.anaconda_version)

  def run(self):
    pass

  def apply(self):
    # set cvars
    self.cvars['installer-repo'] = self.repos['installer']
    self.cvars['anaconda-version-supplied'] = self.anaconda_version

  def verify_cvars(self):
    "verify cvars exist"
    self.verifier.failUnless(self.cvars['installer-repo'])
    # don't check anaconda-version-supplied, may be none
