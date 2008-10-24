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

from spin.callback import GpgCallback
from spin.errors   import SpinError, SpinIOError, assert_file_has_content
from spin.event    import Event
from spin.logging  import L1, L2
from spin.validate import InvalidConfigError

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['GpgCheckEvent'],
  description = 'gpgchecks pkglist RPMs',
  group       = 'repository',
)

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      parentid = 'repository',
      version = '0.9',
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

    gpgkeys = {}   # keys to download
    self.rpms = {} # rpms to check

    for repo in self.cvars['repos'].values():
      if self.cvars['rpms-by-repoid'].has_key(repo.id) and repo.gpgcheck:
        if repo.gpgkey:
          gpgkeys[repo.id] = repo.gpgkey
          self.rpms[repo.id] = self.cvars['rpms-by-repoid'][repo.id]
        else:
          raise NoGpgkeysProvidedError(repo.id)

    for repo in gpgkeys:
      self.io.add_fpaths(gpgkeys[repo], self.mddir/repo, id=repo)
    self.DATA['variables'].append('rpms')

  def run(self):
    if not self.rpms:
      self.io.clean_eventcache(all=True) # remove old keys
      return

    for repo in sorted(self.rpms.keys()):
      newrpms = []
      homedir = self.mddir/repo/'homedir'
      self.DATA['output'].append(homedir)
      newkeys = self.io.sync_input(cache=True, what=repo,
                  text="downloading gpgkeys - '%s'" % repo)

      # if new gpgkeys are downloaded, recreate the homedir and all rpms from
      # that repo to check list
      if newkeys:
        newrpms = self.rpms[repo]
        homedir.rm(force=True, recursive=True)
        homedir.mkdirs()
        for key in self.io.list_output(what=repo):
          assert_file_has_content(key, srcfile=self.io.i_dst[key].src,
                                    cls=GpgkeyIOError)
          self._strip_key(key) # strip off non-gpg information from key
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
          raise RpmSignatureInvalidError('* ' + '\n * '.join(
                                         [ x.basename for x in invalids ]))

  def apply(self):
    self.io.clean_eventcache()

  def _strip_key(self, k):
    "Strip off non-GPG data from GPG keys"
    outlines = []
    inkey = False

    PGP_BEGIN = '-----BEGIN PGP'
    PGP_END   = '-----END PGP'

    for line in k.read_lines():
      if inkey:
        outlines.append(line)
        if line.startswith(PGP_END):
          inkey = False
      else:
        if line.startswith(PGP_BEGIN):
          inkey = True
          outlines.append(line)

    k.write_lines(outlines)

#------ ERRORS ------#
class RpmSignatureInvalidError(SpinError):
  message = "One or more RPMs failed GPG key check:\n %(rpms)s"

class GpgkeyIOError(SpinIOError):
  message = "cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"

class NoGpgkeysProvidedError(SpinError, InvalidConfigError):
  message = "gpgcheck enabled but no gpgkeys defined for repo '%(repoid)s'"
