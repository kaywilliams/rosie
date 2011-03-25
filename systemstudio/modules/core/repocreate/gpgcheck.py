#
# Copyright (c) 2011
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
import cPickle
import rpm
import rpmUtils
import yum

from systemstudio.errors   import SystemStudioError, SystemStudioIOError, assert_file_has_content
from systemstudio.event    import Event
from systemstudio.sslogging  import L1

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
  description = 'gpgchecks pkglist RPMs',
  group       = 'repocreate',
)

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      parentid = 'repocreate',
      version = '1.01',
      requires = ['rpms', 'repos', 'gpgkey-infix', 'gpgcheck-enabled',],
      provides = ['checked-rpms', 'os-content'],
      suppress_run_message = True
    )

    self.DATA = {
      'variables': ['cvars[\'rpms\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    if not self.cvars['gpgcheck-enabled']:
      return

    self.diff.setup(self.DATA)

    for repo in self.cvars['repos'].values():
      for url in repo.gpgkey:
        self.io.add_fpath(url, 
                          self.SOFTWARE_STORE/eval(self.cvars['gpgkey-infix']),
                          id='gpgkeys')

  def run(self):
    if not self.cvars['gpgcheck-enabled']: 
      self.io.clean_eventcache(all=True)
      return

    self.log(1, "gpgcheck")
    #get rpms to check
    self._get_tochecks()

    # sync new keys
    self.io.sync_input(cache=True, callback=self.link_callback, 
                       text="downloading keys")

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

  def apply(self):
    self.io.clean_eventcache()

  def _get_tochecks(self):
    difftup = self.diff.variables.difference('cvars[\'rpms\']')
    if difftup:
      md, curr = difftup
      if not hasattr(md, '__iter__'): md = {}
      self.tochecks = sorted(set(curr).difference(set(md)))
    else:
      self.tochecks = self.cvars['rpms']

  def _process_keys(self):
    # create rpmdb for key storage
    rpmdb_dir = self.mddir/'rpmdb'
    rpmdb_dir.rm(force=True)
    rpmdb_dir.mkdirs()
    rpm.addMacro('_dbpath', rpmdb_dir)
    self.ts = rpm.TransactionSet()
    self.ts.initDB()

    #add keys to rpmdb
    keyids = set()
    for key in self.io.list_output(what='gpgkeys'):
      #validate key
      assert_file_has_content(key, srcfile=self.io.i_dst[key].src,
                              cls=GpgkeyIOError)
      self._strip_key(key) # strip off non-gpg information from key

      #track keyids across sessions for determining when to recheck rpms
      keyids.add(yum.misc.keyIdToRPMVer(
                   yum.misc.getgpgkeyinfo(
                   key.read_text())['keyid']).lower())
      #add to rpmdb
      self.ts.pgpImportPubkey(yum.misc.procgpgkey(key.read_text()))
      
    #cleanup 
    rpm.delMacro('_dbpath')
    self.DATA['output'].append(rpmdb_dir)    

    #if any prior key ids no longer exist, recheck all packages
    priorids = set()
    pklfile = self.mddir/'keyids.pkl'
    if pklfile.exists():
      priorids = cPickle.load(pklfile.open('rb')) # redefine priorids
    if priorids.difference(keyids):
      self.tochecks = self.cvars['rpms']

    #pickle current keyids for future comparison
    pklfile.rm(force=True)
    cPickle.dump(keyids, pklfile.open('wb'), -1)
    self.DATA['output'].append(pklfile)

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
class RpmSignatureInvalidError(SystemStudioError):
  message = "One or more RPMs failed GPG key check. You may need to list additional gpgkeys in your repo definition(s). \n %(rpms)s"

class GpgkeyIOError(SystemStudioIOError):
  message = "Cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"
