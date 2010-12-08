#
# Copyright (c) 2010
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
from systembuilder.util import pps
from systembuilder.util import mkrpm

from systembuilder.util.mkrpm       import GpgMixin
from systembuilder.util.progressbar import ProgressBar

from systembuilder.callback  import GpgCallback, SyncCallback, LAYOUT_GPG
from systembuilder.errors    import assert_file_has_content, SystemBuilderError, SystemBuilderIOError
from systembuilder.event     import Event
from systembuilder.logging   import L1, L2

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['GpgSetupEvent', 'GpgSignEvent'],
  description = 'gpgsigns pkglist RPMs',
  group       = 'repocreate',
)

class GpgSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign-setup',
      parentid = 'setup',
      suppress_run_message = True,
      provides = ['gpgsign-public-key',
                  'gpgsign-secret-key',
                  'gpgsign-passphrase'],
    )


  def setup(self):
    # checks to ensure gpgkeys exist
    self.io.validate_input_file(self.config.getpath('public-key', None))
    self.io.validate_input_file(self.config.getpath('secret-key', None))

  def apply(self):
    self.cvars['gpgsign-public-key'] = self.config.getpath('public-key', None)
    self.cvars['gpgsign-secret-key'] = self.config.getpath('secret-key', None)
    if self.config.pathexists('passphrase'):
      self.cvars['gpgsign-passphrase'] = self.config.get('passphrase/text()', '')

  def verify_cvars(self):
    "public and secret key cvars defined"
    self.verifier.failUnlessSet('gpgsign-public-key')
    self.verifier.failUnlessSet('gpgsign-secret-key')


class GpgSignEvent(GpgMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign',
      parentid = 'repocreate',
      requires = ['cached-rpms', 'gpgsign-public-key',
                  'gpgsign-secret-key', 'gpgsign-passphrase'],
      conditionally_comes_after = ['gpgcheck'],
      provides = ['signed-rpms'],
    )

    self.gpgsign_cb = GpgCallback(self.logger)

    GpgMixin.__init__(self)

    self.DATA = {
      'input':     [],
      'output':    [],
      'config':    ['.'],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.io.add_fpath(self.cvars['gpgsign-public-key'], self.mddir, id='pubkey')
    self.io.add_fpath(self.cvars['gpgsign-secret-key'], self.mddir, id='seckey')

    self.io.add_fpaths(self.cvars['cached-rpms'], self.mddir/'rpms', id='rpms')

    self.io.add_fpath(self.cvars['gpgsign-public-key'],
        self.SOFTWARE_STORE,
        id='gpgsign-software-store')

  def run(self):
    # sync keys
    newkeys = self.io.sync_input(what=['pubkey','seckey'], cache=True,
              text='downloading keys')

    # import keys
    gnupg_dir = self.mddir / '.gnupg'
    pubkey = self.io.list_output(what='pubkey')[0]
    seckey = self.io.list_output(what='seckey')[0]
    if newkeys:
      gnupg_dir.rm(recursive=True, force=True)
      gnupg_dir.mkdirs()
      for key in [pubkey, seckey]:
        assert_file_has_content(key, cls=GpgkeyIOError,
                                srcfile=self.io.i_dst[key].src)
        try:
          self.import_key(gnupg_dir, key)
        except RuntimeError: # raised if key is invalid
          raise GpgkeyInvalidError(self.io.i_dst[key].src)
    self.DATA['output'].append(gnupg_dir)

    # check passphrase if supplied
    if self.cvars['gpgsign-passphrase']:
      if not mkrpm.verifyPassphrase(gnupg_dir, self.cvars['gpgsign-passphrase']):
        raise IncorrectPassphraseError(self.io.i_dst[seckey].src)

    # sync rpms to output folder
    newrpms = self.io.sync_input(what='rpms', text='copying rpms',
              callback=self.copy_callback_compressed)

    # sign rpms
    if newkeys:
      signrpms = self.io.list_output(what='rpms')
    else:
      signrpms = newrpms

    if signrpms:
      self.log(1, L1("signing rpms"))
      if self.cvars['gpgsign-passphrase'] is None: # prompt for password
        while True:
          self.cvars['gpgsign-passphrase'] = mkrpm.getPassphrase()
          if mkrpm.verifyPassphrase(gnupg_dir, self.cvars['gpgsign-passphrase']):
            break
      mkrpm.signRpms(signrpms, homedir=gnupg_dir, passphrase=self.cvars['gpgsign-passphrase'],
                     callback=self.gpgsign_cb, working_dir=self.TEMP_DIR)

    # add key to os folder
    self.io.sync_input(what='gpgsign-software-store', cache=True,
        text="adding public key to 'os' folder")

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['signed-rpms'] = self.io.list_output(what='rpms')

  def verify_gpgkeys_signed(self):
    "gpgkeys exist and were signed"
    for file in self.io.list_output(what='rpms'):
      self.verifier.failUnlessExists(file)
    # TODO: check that RPMs are actually signed

class GpgkeyIOError(SystemBuilderIOError):
  message = "cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"

class GpgkeyInvalidError(SystemBuilderError):
  message = "file '%(file)s' does not appear to be a valid gpg key"

class IncorrectPassphraseError(SystemBuilderError):
  message = "the passphrase provided for gpgkey '%(file)s' is not valid"
