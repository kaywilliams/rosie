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
from rendition import mkrpm
from rendition import shlib

from spin.callback  import GpgCallback
from spin.constants import BOOLEANS_TRUE
from spin.event     import Event
from spin.logging   import L1, L2

API_VERSION = 5.0
EVENTS = {'software': ['GpgCheckEvent']}

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      version = 1,
      requires = ['rpms-by-repoid', 'repos'],
    )

    self.DATA = {
      'variables': [],
      'input':     [],
      'output':    [],
    }

    self.gpgcheck_cb = GpgCallback(self.logger)

  def setup(self):
    self.diff.setup(self.DATA)

    self.gpgkeys = {}  # keys to download
    self.rpms = {}     # rpms to check

    for repo in self.cvars['repos'].values():
      if self.cvars['rpms-by-repoid'].has_key(repo.id) and \
         repo.gpgcheck in BOOLEANS_TRUE:
        if repo.gpgkey:
          self.gpgkeys[repo.id] = repo.gpgkey
          self.rpms[repo.id] = self.cvars['rpms-by-repoid'][repo.id]
        else:
          raise RuntimeError("GPGcheck enabled for '%s' repository, but no "
                             "keys provided." % repo.id)

    for repo in self.gpgkeys.keys():
      self.io.add_fpaths(self.gpgkeys[repo], self.mddir/repo, id=repo)
    self.DATA['variables'].append('rpms')
    self.DATA['variables'].append('gpgkeys')

  def run(self):
    if not self.rpms:
      self.io.clean_eventcache(all=True) # remove old keys
      return

    for repo in sorted(self.rpms.keys()):
      newrpms = []
      homedir = self.mddir/repo/'homedir'
      self.DATA['output'].append(homedir)
      self.io.sync_input(cache=True, what=repo,
                         text="downloading gpgkeys - '%s'" % repo)

      # if gpgkeys have changed for this repo, (re)create homedir and
      # add all rpms from the repo to check list
      difftup = self.diff.variables.difference('gpgkeys')
      if difftup:
        md, curr = difftup
        if not hasattr(md, '__iter__') or not md.has_key(repo):
          md = {repo: []}
        if set(curr[repo]).difference(set(md[repo])):
          newrpms = self.rpms[repo]
          homedir.rm(force=True, recursive=True)
          homedir.mkdirs()
          for key in self.io.list_output(what=repo):
            shlib.execute('gpg --homedir %s --import %s' %(homedir,key))

      # if new rpms have been added from this repo, add them to check list
      else:
        difftup = self.diff.variables.difference('rpms')
        if difftup:
          md, curr = difftup
          if not hasattr(md, '__iter__'): md = {}
          if md.has_key(repo):
            newrpms = sorted(set(curr[repo]).difference(set(md[repo])))

      # if we found rpms to check in the above tests, check them now
      if newrpms:
        self.log(1, L1("checking rpms - '%s'" % repo))
        invalids = mkrpm.verifyRpms(newrpms, homedir=homedir,
                                    callback=self.gpgcheck_cb,
                                    working_dir=self.TEMP_DIR)
        if invalids:
          raise RpmSignatureInvalidError("One or more RPMS failed "
                                         "GPG key checking:\n * %s" % '\n * '.join(invalids))

  def apply(self):
    self.io.clean_eventcache()

#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
