#
# Copyright (c) 2011
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
import subprocess

from StringIO import StringIO

from centosstudio import locals

from centosstudio.util import magic
from centosstudio.util import pps
from centosstudio.util import shlib 
from centosstudio.util.rxml import datfile
from centosstudio.util.rxml.errors import XmlPathError

from centosstudio.event        import Event
from centosstudio.event.fileio import MissingXpathInputFileError

from centosstudio.cslogging    import L2
from centosstudio.errors       import assert_file_readable, CentOSStudioError
from centosstudio.validate     import InvalidConfigError

from centosstudio.modules.shared.config import ConfigEventMixin

import cPickle
import hashlib
import yum

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ConfigRpmEvent'],
  description = 'creates a configuration RPM',
  group       = 'rpmbuild',
)

class ConfigRpmEvent(ConfigEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'config-rpm',
      parentid = 'rpmbuild',
      version = '1.26',
      provides = ['rpmbuild-data', 'config-release', 'gpgkeys',
                  'gpgcheck-enabled', 'gpgsign', 'os-content'],
      requires = ['input-repos', 'publish-setup-options'],
    )

    self.DATA = {
      'variables': ['name', 'fullname', 'rpm.release',],
      'config':    [], # set by ConfigEventMixin
      'input':     [],
      'output':    [],
    }

    ConfigEventMixin.__init__(self) 

  def setup(self):
    self.get_signing_keys()

    ConfigEventMixin.setup(self, 
      webpath=self.cvars['publish-setup-options']['webpath'])

  def run(self):
    self.DATA['output'].extend([self.pubkey, self.seckey])
    ConfigEventMixin.run(self)

  def apply(self):
    self.rpm._apply()

    self.cvars['config-release'] = (self.cvars['rpmbuild-data']['config-rpm']
                                              ['rpm-release'])

    if self.pklfile.exists():
      fo = self.pklfile.open('rb')
      self.cvars['gpgkeys']=cPickle.load(fo)
      fo.close()
    else:
      self.cvars['gpgkeys']=[]

  def verify_pubkey_exists(self):
    "pubkey exist"
    self.verifier.failUnlessExists(self.pubkey)

  def verify_seckey_exists(self):
    "seckey exist"
    self.verifier.failUnlessExists(self.seckey)

  #------- Helper Methods -------#

  def get_signing_keys(self):
    self.pubkey = self.mddir/'RPM-GPG-KEY-%s' % self.solutionid
    self.seckey = self.mddir/'RPM-GPG-KEY-%s-secret' % self.solutionid
    if not hasattr(self, 'datfile'): 
      self.datfile = datfile.parse(self._config.file)

    if self.config.get('gpgsign', None) is None:
      self.get_keys_from_datfile() or self.create_keys()
      self.passphrase=''
    else:
      self.get_keys_from_config() # also sets self.passphrase

    self.DATA['input'].extend([self.pubkey, self.seckey])
    self.DATA['variables'].append('passphrase')

    self.cvars['gpgsign'] = { 'pubkey': self.pubkey,
                              'seckey': self.seckey,
                              'passphrase': self.passphrase }

  def get_keys_from_config(self):
    pubtext = self.config.get('gpgsign/public/text()', '')
    sectext = self.config.get('gpgsign/secret/text()', '')
    self.write_keys(pubtext, sectext)
    self.validate_keys(map = { self.pubkey: 'public', self.seckey: 'secret' })

    if self.config.get('gpgsign/passphrase/text()', None) is None:
      self.passphrase=''
    else:
      self.passphrase = self.config.get('gpgsign/passphrase')

    # remove generated keys from datfile, if exist
    for key in ['pubkey', 'seckey']:
      elem = self.datfile.get('/*/rpms/%s/%s' % (self.id, key), None)
      if elem is not None:
        elem.getparent().remove(elem)

    self.datfile.write()

  def get_keys_from_datfile(self):
    try:
      pubtext = self.datfile.get('/*/rpms/%s/pubkey/text()' % self.id,)
      sectext = self.datfile.get('/*/rpms/%s/seckey/text()' % self.id,)
    except XmlPathError:
      return False # no keys in datfile
   
    self.write_keys(pubtext, sectext)

    return True # keys in datfile

  def create_keys(self):
    homedir = self.mddir/'homedir'
    pubring = homedir/'pubring.gpg'
    secring = homedir/'secring.gpg'

    homedir.rm(recursive=True, force=True)
    homedir.mkdir()
    homedir.chmod(0700)

    name = "%s signing key" % self.solutionid

    cmd = """gpg --batch --gen-key <<EOF
     Key-Type: DSA
     Key-Length: 1024
     Subkey-Type: ELG-E
     Subkey-Length: 1024
     Name-Real: %s
     Expire-Date: 0
     %%pubring %s
     %%secring %s
EOF""" % (name, pubring, secring)

    self.logger.log(2, L2('generating GPG Signing Key'))
    r = subprocess.call(cmd, shell=True)
    if r != 0 : raise RuntimeError

    shlib.execute('gpg --export -a --homedir %s "%s" > %s' % (homedir, name,
                   self.pubkey))
    shlib.execute('gpg --export-secret-key -a --homedir %s "%s" > %s' % (
                   homedir, name, self.seckey))

    # write to datfile
    root = self.datfile
    uElement = datfile.uElement

    rpms     = uElement('rpms', parent=root)
    parent   = uElement(self.id, parent=rpms)
    pubkey   = uElement('pubkey', parent=parent, text=self.pubkey.read_text())
    seckey   = uElement('seckey', parent=parent, text=self.seckey.read_text())

    root.write()

  def write_keys(self, pubtext, sectext):
    if not self.pubkey.exists() or not pubtext == self.pubkey.read_text():
      self.pubkey.write_text(pubtext)
    if not self.seckey.exists() or not sectext == self.seckey.read_text():
      self.seckey.write_text(sectext)

  def validate_keys(self, map):
    for key in map:
      if not magic.match(key) == magic.FILE_TYPE_GPGKEY:
        raise InvalidKeyError(map.value())

class InvalidKeyError(CentOSStudioError):
  message = "The %(type)s key provided does not appear to be valid."
