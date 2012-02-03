#
# Copyright (c) 2011
# CentOS Solutions, Inc. All rights reserved.
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
import os 
import signal 
import subprocess

from centosstudio.util import magic
from centosstudio.util import pps 
from centosstudio.util import shlib 
from centosstudio.util.rxml import datfile
from centosstudio.util.rxml.errors import XmlPathError

from centosstudio.cslogging    import L1
from centosstudio.errors       import CentOSStudioError
from centosstudio.validate     import InvalidConfigError

from centosstudio.event import Event, CLASS_META

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['RpmbuildEvent'],
  description = 'modules that create system-specific RPMs',
)

class RpmbuildEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'rpmbuild',
      parentid = 'os-events',
      ptr = ptr,
      properties = CLASS_META,
      version = '1.00',
      requires = ['publish-setup-options'],
      provides = ['rpmbuild-data','gpg-signing-keys', 'os-content', 
                  'build-machine-data', ],
      suppress_run_message = False 
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'variables': [],
      'output':    []
    }
  
  def validate(self):
    self.definition = self.config.get('definition/text()','')
    if self.type == 'component' and not self.definition:
      raise InvalidConfigError(self.config.getroot().file,
      "\n[%(id)s] Validation Error: a 'definition' element is required "
      "when the value of main/type is set to 'component'." % {'id': self.id,})

  def setup(self):
    self.diff.setup(self.DATA)
    self.cvars['rpmbuild-data'] = {}

    self.pubkey = self.mddir/'RPM-GPG-KEY-%s' % self.solutionid
    self.seckey = self.mddir/'RPM-GPG-KEY-%s-secret' % self.solutionid
    if self.config.get('gpgsign/passphrase/text()', None) is None:
      self.passphrase=''
    else:
      self.passphrase = str(self.config.get('gpgsign/passphrase/text()'))

    self.DATA['variables'].extend(['pubkey', 'seckey', 'passphrase'])

  def run(self):
    self.get_signing_keys()
    self.DATA['output'].extend([self.pubkey, self.seckey])

  def apply(self):
    self.cvars['gpg-signing-keys'] = { 'pubkey': self.pubkey,
                                       'seckey': self.seckey,
                                       'passphrase': self.passphrase }
    self.cvars.setdefault('build-machine-data', {})[
                          'definition'] = self.definition

  def verify_pubkey_exists(self):
    "pubkey exist"
    self.verifier.failUnlessExists(self.pubkey)

  def verify_seckey_exists(self):
    "seckey exist"
    self.verifier.failUnlessExists(self.seckey)

  #------- Helper Methods -------#

  def get_signing_keys(self):
    if not hasattr(self, 'datfile'): 
      self.datfile = datfile.parse(self._config.file)

    if self.config.get('gpgsign', None) is None:
      self.get_keys_from_datfile() or self.create_keys()
    else:
      self.get_keys_from_config() 

  def get_keys_from_config(self):
    pubtext = self.config.get('gpgsign/public/text()', '')
    sectext = self.config.get('gpgsign/secret/text()', '')
    self.write_keys(pubtext, sectext)
    self.validate_keys(map = { self.pubkey: 'public', self.seckey: 'secret' })


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

    cmd = """gpg --quiet --batch --gen-key <<EOF
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
      if not magic.match(key) == eval(
        'magic.FILE_TYPE_GPG%sKEY' % map[key][:3].upper()):
        raise InvalidKeyError(map[key])

class InvalidKeyError(CentOSStudioError):
  message = "The %(type)s key provided does not appear to be valid."
