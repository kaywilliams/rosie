from rendition import pps
from rendition import mkrpm

from rendition.mkrpm import GpgMixin
from rendition.progressbar   import ProgressBar

from spin.callback  import GpgCallback, SyncCallback, LAYOUT_GPG
from spin.constants import BOOLEANS_TRUE, RPM_REGEX
from spin.event     import Event
from spin.logging   import L1, L2

API_VERSION = 5.0
EVENTS = {'setup': ['GpgSetupEvent'], 'software': ['GpgSignEvent']}

P = pps.Path

class GpgSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign-setup',
      suppress_run_message = True,
      provides = ['gpgsign-public-key',
                  'gpgsign-secret-key',
                  'gpgsign-passphrase'],
    )

  def apply(self):
    pubkey = self.config.get('gpg-public-key/text()', None)
    if pubkey: self.cvars['gpgsign-public-key'] = P(pubkey)

    seckey = self.config.get('gpg-secret-key/text()', None)
    if seckey: self.cvars['gpgsign-secret-key'] = P(seckey)

    if self.config.pathexists('gpg-passphrase'):
      pw = self.config.get('gpg-passphrase/text()', '')
      if pw is None: pw = '' # config.get returns None if empty
      self.cvars['gpgsign-passphrase'] = pw

  def verify_cvars(self):
    "public and secret key cvars defined"
    self.verifier.failUnless(self.cvars['gpgsign-public-key'])
    self.verifier.failUnless(self.cvars['gpgsign-secret-key'])


class GpgSignEvent(GpgMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgsign',
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
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.io.add_fpaths(self.cvars['gpgsign-public-key'], self.mddir, id='pubkey')
    self.io.add_fpaths(self.cvars['gpgsign-secret-key'], self.mddir, id='seckey')

    self.io.add_fpaths(self.cvars['cached-rpms'], self.mddir/'rpms', id='rpms')

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
      self.import_key(gnupg_dir, pubkey)
      self.import_key(gnupg_dir, seckey)
    self.DATA['output'].append(gnupg_dir)

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
      self.gpgsign_cb.start()
      if self.cvars['gpgsign-passphrase'] is None:
        while True:
          self.cvars['gpgsign-passphrase'] = mkrpm.getPassphrase()
          if mkrpm.VerifyPassphrase(gnupg_dir, self.cvars['gpgsign-passphrase']):
            break
      self.gpgsign_cb.repoCheck(len(signrpms))
      for rpm in signrpms:
        mkrpm.SignRpm(rpm,
                      homedir=gnupg_dir,
                      passphrase=self.cvars['gpgsign-passphrase'])
        self.gpgsign_cb.pkgChecked(rpm.basename)
      self.gpgsign_cb.endRepo()
      self.gpgsign_cb.end()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['signed-rpms'] = self.io.list_output(what='rpms')

  def verify_gpgkeys_signed(self):
    "gpgkeys exist and were signed"
    for file in self.io.list_output(what='rpms'):
      self.verifier.failUnlessExists(file)
    # TODO: check that keys are actually signed
