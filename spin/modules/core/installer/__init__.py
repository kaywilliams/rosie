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
      provides = [ 'installer-repo', ],
      conditionally_requires = [ 'base-distro-name',
                                 'base-distro-version',
                                 'base-distro-baseurl',
                                 'base-distro-mirrorlist' ],
      suppress_run_message = True,
    )

    self.DATA = {
      'input': [],
      'output': [],
      'variables': [],
      'config': ['.'],
    }

    RepoEventMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    args   = ['installer']
    kwargs = dict(cls=repo.IORepo, read_md=False)

    if self.config.pathexists('baseurl/text()') or \
       self.config.pathexists('mirrorlist/text()'):
      args.extend([None, None]) # set distro and version to none
      kwargs.update({'baseurl':    self.config.get('baseurl/text()', None),
                     'mirrorlist': self.config.get('mirrorlist/text()', None)})
    else:
      args.extend([self.cvars['base-distro-name'],
                   self.cvars['base-distro-version']])
      kwargs.update({'baseurl_prefix':    self.cvars['base-distro-baseurl'],
                     'mirrorlist_prefix': self.cvars['base-distro-mirrorlist']})

    self.setup_repos(*args, **kwargs)

  def run(self):
    pass

  def apply(self):
    # set cvars
    self.cvars['installer-repo'] = self.repos['installer']

  def verify_cvars(self):
    "verify cvars exist"
    self.verifier.failUnless(self.cvars['installer-repo'])
