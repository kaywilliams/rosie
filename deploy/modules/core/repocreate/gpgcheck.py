#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

from deploy.dlogging  import L1
from deploy.errors    import DeployEventError, DeployIOError
from deploy.event     import Event

from deploy.modules.shared import GPGKeysEventMixin 

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['GpgcheckEvent'],
    description = 'downloads package list RPMs',
    group       = 'repocreate',
  )

class GpgcheckEvent(Event, GPGKeysEventMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'gpgcheck',
      version = 1.01,
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['checked-rpms'],
      requires = ['rpmsdir', 'rpms'],
      conditionally_requires = ['gpgcheck-enabled'],
    )

    self.DATA = {
      'variables': set(["cvars['rpmsdir']", "cvars['rpms']"]),
      'input':     set(),
      'output':    set(),
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.rpmdb_dir = self.mddir / 'rpmdb'
    if getattr(self, 'cvars[\'gpgcheck-enabled\']', True):
      self.DATA['variables'].add('cvars[\'gpgcheck-enabled\']')
      GPGKeysEventMixin.setup(self)

  def run(self):
    if not self.cvars['gpgcheck-enabled']:
      self.rpmdb_dir.rm(force=True, recursive=True)
      self.ts=None
      return

    self._get_tochecks()
    self._process_keys()
    self._process_packages()

  def _get_tochecks(self):
    self.tochecks = []
    if "cvars['rpms']" in self.diff.variables.difference():
      md, curr = self.diff.variables.difference()["cvars['rpms']"]
      self.tochecks = set(curr).difference(md) # new rpms have been added

  def _process_keys(self):
    # if any prior key ids no longer exist, start clean to force rechecking
    if "keyids" in self.diff.variables.difference():
      md, curr = self.diff.variables.difference()['keyids']
      if set(md).difference(curr): #prior key has been removed
        self.log(4, L1("gpgkey(s) removed - rechecking all packages"))
        self.io.clean_eventcache(all=True)
        self.tochecks = self.cvars['rpms'].keys()

    # create rpmdb for key storage
    self.ts = rpmUtils.transaction.TransactionWrapper(root=self.rpmdb_dir)

    #add keys to rpmdb
    for key in self.keyids:
      self.ts.pgpImportPubkey(yum.misc.procgpgkey(key))

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
class RpmSignatureInvalidError(DeployEventError):
  message = ("The '%(pkg)s' package from the '%(repo)s' repository failed GPG "
             "key check. The error was '%(error)s'. \n\nYou may need to list "
             "additional gpgkeys in the repo element(s) in your definition. "
             "Alternatively, you can disable GPG key checking using the "
             "release-rpm element. See the Deploy Definition File Reference "
             "for additional information.")

class GpgkeyIOError(DeployIOError):
  message = "Cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"
