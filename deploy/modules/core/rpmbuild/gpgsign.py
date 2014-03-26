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
import os
import signal 
import subprocess

from deploy.util import magic
from deploy.util import pps 
from deploy.util import shlib 

from deploy.util.rxml import config 
from deploy.util.rxml.errors import XmlPathError

from deploy.dlogging    import L1
from deploy.errors       import DeployEventError

from deploy.event import Event


def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['GpgSignSetupEvent'],
    description = 'gets or creates gpg signing keys',
  )


class GpgSignSetupEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'gpgsign',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = '1.01',
      provides = ['gpg-signing-keys', 'os-content',],
      suppress_run_message = False 
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'variables': [],
      'output':    []
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.pubkey = self.mddir/'RPM-GPG-KEY-%s' % self.build_id
    self.seckey = self.mddir/'RPM-GPG-KEY-%s-secret' % self.build_id
    if self.config.getxpath('passphrase/text()', None) is None:
      self.passphrase=''
    else:
      self.passphrase = str(self.config.getxpath('passphrase/text()'))

    (self.get_keys_from_config() or 
     self.get_keys_from_datfile() or 
     self.create_keys())

    self.DATA['variables'].extend(['pubtext', 'sectext', 'pubkey', 'seckey',
                                   'passphrase'])

  def run(self):
    self.write_keys(self.pubtext, self.sectext)
    self.validate_keys(map = { self.pubkey: 'public', self.seckey: 'secret' })
    self.DATA['output'].extend([self.pubkey, self.seckey])

  def apply(self):
    self.cvars['gpg-signing-keys'] = { 'pubkey': self.pubkey,
                                       'seckey': self.seckey,
                                       'passphrase': self.passphrase }

  def verify_pubkey_exists(self):
    "pubkey exist"
    self.verifier.failUnlessExists(self.pubkey)

  def verify_seckey_exists(self):
    "seckey exist"
    self.verifier.failUnlessExists(self.seckey)

  #------- Helper Methods -------#

  def get_keys_from_config(self):
    self.pubtext = self.config.getxpath('public/text()', '')
    self.sectext = self.config.getxpath('secret/text()', '')

    if not (self.pubtext and self.sectext):
      return False

    # else, remove generated keys from datfile, if exist, and return true
    df = self.parse_datfile()
    for key in ['pubkey', 'seckey']:
      elem = df.getxpath('/*/%s/%s' % (self.id, key), None)
      if elem is not None:
        elem.getparent().remove(elem)
    self.write_datfile(df)
    return True

  def get_keys_from_datfile(self):
    df = self.parse_datfile()
    self.pubtext = df.getxpath('/*/%s/pubkey/text()' % self.id, '')
    self.sectext = df.getxpath('/*/%s/seckey/text()' % self.id, '')

    if not (self.pubtext and self.sectext):
      return False # no keys in datfile

    return True # keys in datfile

  def create_keys(self):
    homedir = self.mddir/'homedir'
    pubring = homedir/'pubring.gpg'
    secring = homedir/'secring.gpg'

    homedir.rm(recursive=True, force=True)
    homedir.mkdir(mode=0700)

    name = "%s signing key" % self.build_id

    cmd = """/usr/bin/gpg --quiet --batch --gen-key <<EOF
     Key-Type: DSA
     Key-Length: 1024
     Subkey-Type: ELG-E
     Subkey-Length: 1024
     Name-Real: %s
     Expire-Date: 0
     %%pubring %s
     %%secring %s
EOF""" % (name, pubring, secring)

    rngd = pps.path('/sbin/rngd')

    self.logger.log(2, L1('generating GPG Signing Key'))
    if rngd.exists():
      # use rngd to speed gpgkey generation, slightly less secure, but
      # sufficient for RPM-GPG-KEY scenarios.
      p = subprocess.Popen([rngd, '-f', '-r', '/dev/urandom'],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
      shlib.execute(cmd)
    finally:
      if rngd.exists(): os.kill(p.pid, signal.SIGTERM)

    shlib.execute('/usr/bin/gpg --batch --export -a --homedir %s "%s" > %s' % 
                 (homedir, name, self.pubkey))
    shlib.execute('/usr/bin/gpg --batch --export-secret-key -a --homedir %s "%s" > %s'
                  % (homedir, name, self.seckey))

    self.pubtext = self.pubkey.read_text()
    self.sectext = self.seckey.read_text()

    # write to datfile
    root = self.parse_datfile()
    uElement = config.uElement

    gpgsign      = uElement(self.id, parent=root)
    pubkey = uElement('pubkey', parent=gpgsign, text=self.pubtext)
    seckey = uElement('seckey', parent=gpgsign, text=self.sectext)
    self.write_datfile(root)

  def write_keys(self, pubtext, sectext):
    if not self.pubkey.exists() or not self.pubkey.read_text() == pubtext:
      self.pubkey.write_text((pubtext.strip() + '\n').encode('utf8'))
    if not self.seckey.exists() or not self.seckey.read_text() == sectext:
      self.seckey.write_text((sectext.strip() + '\n').encode('utf8'))

  def validate_keys(self, map):
    for key in map:
      # TODO - the InvalidKeyError message is potentially misleading as 
      # we are validating both provided and generated keys 
      if not magic.match(key) == eval(
        'magic.FILE_TYPE_GPG%sKEY' % map[key][:3].upper()):
        raise InvalidKeyError(type=map[key], text=key.read_text())


# -------- Error Classes --------#
class InvalidKeyError(DeployEventError):
  message = ("The provided %(type)s signing key is invalid:\n\n%(text)s ")
