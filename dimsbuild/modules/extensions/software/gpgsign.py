from dims import pps
from dims import mkrpm

from dims.mkrpm import GpgMixin
from dims.progressbar   import ProgressBar

from dimsbuild.callback  import GpgCallback, FilesCallback, SyncCallback,\
                                LAYOUT_GPG
from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event
from dimsbuild.logging   import L1, L2

API_VERSION = 5.0
EVENTS = {'setup': ['GpgSetupEvent'], 'software': ['GpgSignEvent']}

P = pps.Path

class GpgSignFilesCallback(FilesCallback):
  def sync_start(self): pass

class GpgSignSyncCallback(SyncCallback):
  """
  Callback class for gpgsign file copy. Displays a single progress bar for all
  files as they are copied.
  """
  def __init__(self, logger, relpath):
    """
    logger  : the logger object to which output should be written
    relpath : the relative path from which file display should begin; in most
              casess, this should be set to the event's metadata directory
    """
    SyncCallback.__init__(self, logger=logger, relpath=relpath)
    self.logger = logger
    self.relpath = relpath

  def startcopy(self, total): 

    """
    At log level 1 and below, do nothing
    At log level 2 and above, create a progress bar and start it.
    
    total : the 'size' of the progress bar (number of rpms)
    """
    if self.logger.test(2):
      self.bar = ProgressBar(size=total, title=L2(''), layout=LAYOUT_GPG)
      self.bar.start()
      self.bar.tags['title'] = L2('copying rpms')
  def cp(self, src, dest): pass
  def sync_update(self, src, dest): pass
  def mkdir(self, src, dest): pass
  def _cp_start(self, size, text, seek=0.0):
    """
    At log level 1 and below, do nothing
    At log level 2 and above, update the progress bar's position
    """
    if self.logger.test(2):
      self.bar.tags['title'] = L2(text)
      self.bar.status.position += 1
  def _cp_update(self, amount_read): pass
  def _cp_end(self, amount_read): pass
  def endcopy(self):
    """
    At log level 1 and below, do nothing
    At log level 2 and above, finish off the progress bar and write it to the
    logfile
    """
    if self.logger.test(2):
      self.bar.tags['title'] = L2('done')
      self.bar.update(self.bar.status.size)
      self.bar.finish()
      self.logger.logfile.log(2, str(self.bar))

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
      self.cvars['gpgsign-passphrase'] = self.config.get('gpg-passphrase/text()', '')

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

    self.io.setup_sync(self.mddir, paths=self.cvars['gpgsign-public-key'],
                       id='pubkey')
    self.io.setup_sync(self.mddir, paths=self.cvars['gpgsign-secret-key'],
                       id='seckey')

    self.io.setup_sync(self.mddir/'rpms', paths=self.cvars['cached-rpms'], id='rpms')

  def run(self):
    # sync keys
    self.log(1, L1("downloading keys"))
    newkeys = self.io.sync_input(what=['pubkey','seckey'], cache=True,
              cb=GpgSignFilesCallback(self.logger, self.mddir/'rpms'))

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
    self.log(1, L1("copying rpms"))
    copy_callback = GpgSignSyncCallback(self.logger, self.mddir/'rpms')
    copy_callback.startcopy(len(self.io.list_output(what='rpms')))
    newrpms = self.io.sync_input(what='rpms',  
              cb=GpgSignFilesCallback(self.logger, self.mddir/'rpms'),
              callback=copy_callback)
    copy_callback.endcopy()

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
