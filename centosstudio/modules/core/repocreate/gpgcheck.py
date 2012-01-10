#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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

from centosstudio.errors   import CentOSStudioError, CentOSStudioIOError, assert_file_has_content
from centosstudio.event    import Event
from centosstudio.cslogging  import L1

YUMCONF_HEADER = [
  '[main]',
  'cachedir=',
  'logfile=/depsolve.log',
  'debuglevel=0',
  'errorlevel=0',
  'gpgcheck=0',
  'tolerant=1',
  'exactarch=1',
  'reposdir=/',
  '\n',
]

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['GpgCheckEvent'],
  description = 'gpgchecks package list RPMs',
  group       = 'repocreate',
)

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      parentid = 'repocreate',
      version = '1.03',
      requires = ['rpms'],
      conditionally_requires = ['gpgcheck-enabled', 'gpgkeys'],
      provides = ['checked-rpms', ],
      suppress_run_message = True
    )

    self.DATA = {
      'variables': ['cvars[\'gpgcheck-enabled\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    if not self.cvars['gpgcheck-enabled']:
      return

    # massage rpms cvar into a form that difftest.variables handles properly
    # in the future we should add pickle support to difftest
    self.rpms = sorted([x for x in self.cvars['rpms']])
    self.DATA['variables'].append('rpms')

    if self.cvars['gpgkeys']:
      self.DATA['input'].extend(self.cvars['gpgkeys'])

  def run(self):
    if not self.cvars['gpgcheck-enabled']: 
      self.io.clean_eventcache(all=True)
      return

    self.log(1, "gpgcheck")
    #get rpms to check
    self._get_tochecks()

    # process keys
    self._process_keys()

    # check signatures 
    error_text = { 1 : 'missing gpgkey',
                   2 : 'error reading package signature',
                   3 : 'untrusted gpgkey',
                   4 : 'unsigned package'}
    if self.tochecks:
      self.log(1, L1("checking packages"))
      invalids = []
      for pkg in self.tochecks:
        r = rpmUtils.miscutils.checkSig(self.ts, pkg)
        if r != 0: # check failed
          invalids.append( (pkg, error_text[r]) )
      self.ts.close()
      del self.ts
      self.ts = None
      if invalids:
        # provide msg listing package name, error type, and originating repo
        repos = {}
        for r in self.cvars['rpms']:
          repos[r.basename] = self.cvars['rpms'][r]
        raise RpmSignatureInvalidError('* ' + '\n * '.join(
                                       [ "%s (%s, %s repo)" % 
                                         (x[0].basename, 
                                          x[1], 
                                          repos[x[0].basename]) 
                                        for x in invalids ]))


  def _get_tochecks(self):
    difftup = self.diff.variables.difference('rpms')
    if difftup:
      md, curr = difftup
      if not hasattr(md, '__iter__'): md = {}
      self.tochecks = sorted(set(curr).difference(set(md)))
    else:
      self.tochecks = self.cvars['rpms']

  def _process_keys(self):
    # create rpmdb for key storage
    self.ts = rpmUtils.transaction.TransactionWrapper(root=self.mddir/'rpmdb')

    # add rpmdb dir to output
    # shouldn't need to do this since we never use it on subsequent runs
    # but for some reason, sporadically, it is being accessed during python
    # garbage collection (even though we close the transaction and 
    # delete and reset the transaction object immediately after use)
    # No harm in leaving it around since we delete it at the start of each 
    # run via clean_metadata(all=true)
    self.DATA['output'].append(self.mddir/'rpmdb')

    #add keys to rpmdb
    for key in self.cvars['gpgkeys']:
      #validate key
      assert_file_has_content(key, cls=GpgkeyIOError)

      #add to rpmdb
      self.ts.pgpImportPubkey(yum.misc.procgpgkey(key.read_text()))
      
    # if any prior key ids no longer exist, recheck all packages
    # this approach is fragile in that it assumes the only input files
    # are gpgkeys, which is true at the moment, but not guaranteed 
    removed = []
    for k in self.diff.input.difference():
      difftup = self.diff.input.difference()[k]
      if difftup:
        md, curr = difftup
        if md and not curr: #prior key has been removed
          removed.append(k)
    if removed:
        self.tochecks = self.cvars['rpms']
        self.log(3, L1("keys removed"))

  def verify_mdfile_exists(self):
    # this is silly but it keeps cstest from complaining 
    self.verifier.failUnlessExists(self.mdfile)

#------ ERRORS ------#
class RpmSignatureInvalidError(CentOSStudioError):
  message = "One or more RPMs failed GPG key check. You may need to list additional gpgkeys in your repo definition(s). \n %(rpms)s"

class GpgkeyIOError(CentOSStudioIOError):
  message = "Cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"
