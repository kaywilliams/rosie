#
# Copyright (c) 2012
# Repo Studio Project. All rights reserved.
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
import rpmUtils
import yum

from repostudio.errors    import (RepoStudioEventError, RepoStudioIOError,
                                    assert_file_has_content)
from repostudio.event     import Event
from repostudio.cslogging import L1

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['GpgcheckEvent'],
    description = 'downloads package list RPMs',
    group       = 'repocreate',
  )

class GpgcheckEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'gpgcheck',
      version = 1.01,
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['checked-rpms'],
      requires = ['pkglist', 'rpmsdir', 'rpms'],
      conditionally_requires = ['gpgcheck-enabled', 'gpgkeys',],
    )

    self.DATA = {
      'variables': ["cvars['rpmsdir']", "cvars['rpms']"],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    # setup for gpgchecking
    self.rpmdb_dir = self.mddir / 'rpmdb'
    if getattr(self, 'cvars[\'gpgcheck-enabled\']', True):
      self.DATA['variables'].append('cvars[\'gpgcheck-enabled\']')
      if self.cvars['gpgkeys']:
        self.DATA['input'].extend(self.cvars['gpgkeys'])

  def run(self):
    if not self.cvars['gpgcheck-enabled']:
      self.rpmdb_dir.rm(force=True, recursive=True)
      self.ts=None
      return

    self._get_tochecks()
    self._process_keys()
    self._process_packages()

  def _get_tochecks(self):
    if "cvars['rpms']" in self.diff.variables.difference():
      md, curr = self.diff.variables.difference()["cvars['rpms']"]
      self.tochecks = set(curr).difference(md) # new rpms have been added

  def _process_keys(self):
    # if any prior key ids no longer exist, start clean to force rechecking
    if "cvars['gpgkey-ids']" in self.diff.variables.difference():
      md, curr = self.diff.variables.difference()['cvars[\'gpgkey-ids\']']
      if set(md).difference(curr): #prior key has been removed
        self.log(1, L1("gpgkey(s) removed - rechecking all packages"))
        self.io.clean_eventcache(all=true)
        self.tochecks = self.cvars['rpms'].keys()

    # create rpmdb for key storage
    self.ts = rpmUtils.transaction.TransactionWrapper(root=self.rpmdb_dir)

    #add keys to rpmdb
    for key in self.cvars['gpgkeys']:
      assert_file_has_content(key, cls=GpgkeyIOError)
      self.ts.pgpImportPubkey(yum.misc.procgpgkey(key.read_text()))

  def _process_packages(self):
    error_text = { 1 : 'missing gpgkey',
                   2 : 'error reading package signature',
                   3 : 'untrusted gpgkey',
                   4 : 'unsigned package'}

    try:
      for pkg in self.tochecks:
        r = rpmUtils.miscutils.checkSig(self.ts, pkg)
        if r != 0: # check failed
          raise RpmSignatureInvalidError(pkg=pkg.basename, 
                                         repo=self.cvars['rpms'][pkg],
                                         error=error_text[r])
    finally:
      if self.ts: 
        self.ts.close()
   

#------ ERRORS ------#
class RpmSignatureInvalidError(RepoStudioEventError):
  message = ("The '%(pkg)s' package from the '%(repo)s' repository failed GPG "
             "key check. The error was '%(error)s'. You may need to list "
             "additional gpgkeys in your repo definition(s).")

class GpgkeyIOError(RepoStudioIOError):
  message = "Cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"
