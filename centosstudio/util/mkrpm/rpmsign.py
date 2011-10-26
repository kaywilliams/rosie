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
"""

This module should be used to sign an RPM, verify the RPM's signature,
or delete the RPM's signature. It also contains the getPassphrase()
function, that can be used to ask the user for the passphrase to be used
while signing the RPM.

Some handy things to know:
  1. To create a GPG key, run 'gpg --gen-key' and follow the
     instructions on the screen.
  2. To export a GPG key, run 'gpg --export -a KEYUID > PUBLIC-KEY'.
  3. To export a private GPG key, run 'gpg --export-secret-key KEYUID
     > PRIVATE-KEY'.
"""

__author__  = 'Uday Prakash <uprakash@centosstudio.org>'
__date__    = 'March 30, 2007'
__version__ = '0.1'

__all__ = [
  'AddHandler',
  'DeleteHandler',
  'GpgMixin',
  'IncorrectPassphraseError',
  'MissingTagError',
  'PassphraseVerifier',
  'RpmSignatureInvalidError',
  'VerifyHandler',
  'deleteSignatures',
  'getPassphrase',
  'signRpms',
  'verifyPassphrase',
  'verifyRpms',
]


STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2

from getpass import getpass

import hashlib 
import os
import tempfile

from centosstudio.util import gpgparse
from centosstudio.util import magic
from centosstudio.util import pps
from centosstudio.util import shlib
from centosstudio.util import sync

from callback import RpmSignCallback
from globals  import RPM_HEADER_INDEX_MAGIC
from package  import RpmPackage as Package

RPMSIGN_DIR = '/tmp/rpmsign'

#--------- HELPER FUNCTIONS ----------#
def getPassphrase():
  """
  Ask the user for the pass phrase, without echoing the characters on
  the screen.
  """
  return getpass("Enter GPG passphrase: ")

def checkPassphrase(homedir, gpgname, passphrase):
  rd, wr = os.pipe()
  pid = os.fork()
  if not pid:
    os.close(STDIN_FILENO)
    os.close(STDOUT_FILENO)
    os.close(STDERR_FILENO)
    os.close(wr)
    for (fileno, mode) in [(STDIN_FILENO, os.O_RDONLY),
                           (STDOUT_FILENO, os.O_WRONLY),
                           (STDERR_FILENO, os.O_WRONLY)]:
      fdno = os.open('/dev/null', mode)
      if fdno != fileno:
        os.dup2(fdno, fileno)
        os.close(fdno)
      os.execv('/usr/bin/gpg',
               ('gpg', '--batch', '--no-verbose', '--passphrase-fd', '%d' %(rd,),
                '--homedir', homedir, '-u', gpgname, '-so', '-',))
      os.close(rd)
  os.close(rd)
  os.write(wr, passphrase)
  os.write(wr, '\n')
  os.close(wr)

  pid2, status = os.waitpid(pid, 0)
  assert pid2 == pid
  return os.WEXITSTATUS(status) == 0


#---------- MIXINS ------------#
class GpgMixin:
  def __init__(self): pass

  def import_keys(self, prefix, public, secret):
    homedir = pps.path(tempfile.mkdtemp(dir=prefix))

    if type(public) != type([]): public = [public]
    if type(secret) != type([]): secret = [secret]

    for p in public: self.import_key(homedir, pps.path(p))
    for s in secret: self.import_key(homedir, pps.path(s))

    return homedir

  def import_key(self, homedir, key):
    homedir.mkdirs()
    sync.sync(key, homedir)
    key = homedir / key.basename
    if not magic.match(key) == magic.FILE_TYPE_GPGKEY:
      raise RuntimeError("file '%s' does not appear to be a gpg key" % key)
    shlib.execute('gpg --homedir %s --import %s' % (homedir, key))

  def get_gpgname(self, homedir, index=0):
    gpg_keys = self.get_gpgkeys(homedir)
    gpg_key = gpg_keys[index]
    return gpg_key.keyid

  def check_gpgname(self, homedir, gpgname):
    for gpg_key in self.get_gpgkeys(homedir):
      if (gpg_key.keyid == gpgname) or \
             (gpg_key.userid.uid.find(gpgname) != -1):
        return True
    return False

  def get_gpgkeys(self, homedir):
    gpg_keys = shlib.execute('gpg --list-keys --with-colons '\
                             '--fixed-list-mode --homedir %s' % homedir)
    keys = gpgparse.parsekeys(gpg_keys)
    if len(keys) == 0:
      raise IOError("no gpg keys found in homedir %s" % homedir)
    return keys


#--------- CLASSES ---------#
class RpmPackage:
  def __init__(self, rpm):
    self.rpm = rpm
    self.package = Package(self.rpm)

  def open(self):
    """
    Open the RPM and read it. This process also verifies that the file
    is indeed an RPM.
    """
    self.package.open('rw+')
    self.package.read()

  def close(self, reset=False):
    """
    Close the RPM, after having verified/modified it.
    """
    self.package.write(dest=self.rpm)
    self.package.close(reset=reset)

class TagComputer(GpgMixin):
  def __init__(self, working_dir, secret_required, **kwargs):
    GpgMixin.__init__(self)

    if kwargs.get('homedir', None) and kwargs.get('public', None):
      raise IOError("the homedir and public key parameters are mutually exclusive")
    if not kwargs.get('homedir', None) and not kwargs.get('public', None):
      raise IOError("either the homedir or the public key parameters must be specified")
    if secret_required and kwargs.get('public', None) and \
        not kwargs.get('secret', None):
      raise IOError("secret key not specified")

    self.working_dir = pps.path(tempfile.mkdtemp(dir=working_dir))

    self.keys_provided = False
    if not kwargs.get('homedir', None):
      kwargs['homedir'] = self.import_keys(self.working_dir,
                                           kwargs['public'],
                                           kwargs.get('secret', []))
      self.keys_provided = True
    self.homedir = pps.path(kwargs['homedir'])

    if not kwargs.has_key('gpgname'):
      kwargs['gpgname'] = self.get_gpgname(self.homedir)
    elif not self.check_gpgname(self.homedir, kwargs['gpgname']):
      raise IOError("incorrect gpgname '%s' specified" % kwargs['gpgname'])
    self.gpgname = kwargs['gpgname']

  def open(self):
    self.headerfile = self.working_dir / 'header'
    self.header     = self.package.generateHeader()
    self.headerfile.write_text(self.header)

    self.contentsfile = self.working_dir / 'header+payload'
    self.contents     = self.header + self.package.generatePayload()
    self.contentsfile.write_text(self.contents)

  def close(self):
    if self.keys_provided:
      self.homedir.rm(recursive=True, force=True)
    self.working_dir.rm(recursive=True, force=True)

  def get_size(self):
    return (long(os.stat(self.contentsfile).st_size),)

  def get_md5(self):
    return hashlib.md5(self.contents).digest()

  def get_gpg(self):
    sigfile = self.get_sigfile(self.contentsfile)
    gpg = sigfile.read_text()
    sigfile.rm(force=True)
    return gpg

  def get_dsa(self):
    sigfile = self.get_sigfile(self.headerfile)
    dsa = sigfile.read_text()
    sigfile.rm(force=True)
    return dsa

  def get_sha1(self):
    return hashlib.sha1(self.header).hexdigest()

  def get_sigfile(self, file):
    sigfile = pps.path('%s.sig' % file)
    rd, wr = os.pipe()
    pid = os.fork()
    if not pid:
      os.close(wr)
      # pipe stdin, stdout and stderr to /dev/null
      os.close(STDIN_FILENO)
      os.close(STDOUT_FILENO)
      os.close(STDERR_FILENO)
      for (fileno, mode) in [(STDIN_FILENO, os.O_RDONLY),
                             (STDOUT_FILENO, os.O_WRONLY),
                             (STDERR_FILENO, os.O_WRONLY)]:
        fdno = os.open('/dev/null', mode)
        if fdno != fileno:
          os.dup2(fdno, fileno)
          os.close(fdno)
      os.execv('/usr/bin/gpg',
               ('gpg', '--batch', '--no-verbose',
                '--passphrase-fd', '%d' %(rd,),
                '--no-secmem-warning', '-u', self.gpgname,
                '--homedir', self.homedir, '-sbo', str(sigfile), file))
      os.close(rd)
    os.close(rd)
    os.write(wr, self.passphrase)
    os.write(wr, '\n')
    os.close(wr)
    pid2, status = os.waitpid(pid,0)
    assert pid2 == pid
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status):
      raise Exception("gpg exec failed (%d)" % os.WEXITSTATUS(status))
    if not sigfile.exists():
      raise Exception("gpg failed to encrypt file %s" % file)
    return sigfile

class TagDeleter:
  def __init__(self): pass

  def delete_tag(self, tag):
    if self.package.signature.has_key(tag):
      self.package.signature.pop(tag)

#------- SIGNATURE HANDLERS -------#
class DeleteHandler(RpmPackage, TagDeleter):
  def __init__(self, rpm):
    RpmPackage.__init__(self, rpm)
    TagDeleter.__init__(self)

  def run(self):
    self.delete_tag('gpg')
    self.delete_tag('dsaheader')

class AddHandler(RpmPackage, TagComputer, TagDeleter):
  def __init__(self, rpm, working_dir, **kwargs):
    RpmPackage.__init__(self, rpm)
    TagComputer.__init__(self, working_dir, True, **kwargs)
    TagDeleter.__init__(self)

    if kwargs.get('passphrase', None) is None:
      kwargs['passphrase'] = getPassphrase()
    self.passphrase = kwargs['passphrase']

  def open(self):
    RpmPackage.open(self)
    TagComputer.open(self)

  def close(self):
    RpmPackage.close(self)
    TagComputer.close(self)

  def verify_passphrase(self):
    return checkPassphrase(self.homedir, self.gpgname, self.passphrase)

  def run(self):
    # verify passphrase
    if not self.verify_passphrase():
      raise IncorrectPassphraseError("passphrase check failed")

    # eliminate legacy tags
    self.delete_tag('badsha1_1')
    self.delete_tag('badsha1_2')

    # compute tag values in signature header
    self.package.signature['size_in_signature'] = self.get_size()
    self.package.signature['md5']         = self.get_md5()
    self.package.signature['sha1header']  = self.get_sha1()
    self.package.signature['gpg']         = self.get_gpg()
    self.package.signature['dsaheader']   = self.get_dsa()

class VerifyHandler(RpmPackage, TagComputer):
  def __init__(self, rpm, working_dir, **kwargs):
    RpmPackage.__init__(self, rpm)
    TagComputer.__init__(self, working_dir, False, **kwargs)

  def open(self):
    RpmPackage.open(self)
    TagComputer.open(self)

  def close(self):
    RpmPackage.close(self, reset=True)
    TagComputer.close(self)

  def run(self, digest=True, signature=True, force=False):
    ok  = []
    nok = []
    if self.get_size() == self.package.signature['size_in_signature']:
      ok.append('size_in_signature')
    else:
      nok.append('size_in_signature')

    if self.get_sha1() == self.package.signature['sha1header']:
      ok.append('sha1header')
    else:
      nok.append('sha1header')

    if digest:
      self.verify_digest(ok, nok, force=force)
    if signature:
      self.verify_signature(ok, nok, force=force)

    if nok:
      raise RpmSignatureInvalidError(
        "RPM %s had an invalid signature. Invalid tags: %s" % \
        (self.rpm, ', '.join(nok)), nok
      )

  def verify_digest(self, ok, nok, force=False):
    if self.package.signature.has_key('md5'):
      if self.package.signature['md5'] == self.get_md5():
        ok.append('md5')
      else:
        nok.append('md5')
    elif force:
      raise MissingTagError("'md5' tag missing from rpm header")

  def verify_signature(self, ok, nok, force=False):
    if self.package.signature.has_key('gpg'):
      if self.check_gpg():
        ok.append('gpg')
      else:
        nok.append('gpg')
    elif force:
      raise MissingTagError("'gpg' tag missing from rpm header")

    if self.package.signature.has_key('dsaheader'):
      if self.check_dsa():
        ok.append('dsaheader')
      else:
        nok.append('dsaheader')
    elif force:
      raise MissingTagError("'dsaheader' tag missing from rpm header")

  def check_gpg(self):
    plaintext  = self.contentsfile
    ciphertext = self.package.signature['gpg']
    return self.compare(plaintext, ciphertext)

  def check_dsa(self):
    plaintext  = self.headerfile
    ciphertext = self.package.signature['dsaheader']
    return self.compare(plaintext, ciphertext)

  def compare(self, plaintext, ciphertext):
    try:
      sigfile = self.working_dir / 'sigfile'
      sigfile.write_text(ciphertext)
      pid = os.fork()
      if not pid:
        # pipe stdin, stdout and stderr to /dev/null
        os.close(STDIN_FILENO)
        os.close(STDOUT_FILENO)
        os.close(STDERR_FILENO)
        for (fileno, mode) in [(STDIN_FILENO, os.O_RDONLY),
                               (STDOUT_FILENO, os.O_WRONLY),
                               (STDERR_FILENO, os.O_WRONLY)]:
          fdno = os.open('/dev/null', mode)
          if fdno != fileno:
            os.dup2(fdno, fileno)
            os.close(fdno)
        os.execv('/usr/bin/gpg', ('gpg', '--homedir', self.homedir,
                                  '--batch', '--no-verbose', '--verify',
                                  '--no-secmem-warning',
                                  str(sigfile), plaintext,))
      pid2, status = os.waitpid(pid, 0)
      assert pid2 == pid
      return os.WEXITSTATUS(status) == 0
    finally:
      sigfile.rm(force=True)

class PassphraseVerifier(GpgMixin):
  def __init__(self, homedir, passphrase, gpgname=None):
    GpgMixin.__init__(self)
    self.homedir = homedir
    self.passphrase = passphrase
    self.gpgname = gpgname or self.get_gpgname(self.homedir)

  def check(self):
    return checkPassphrase(self.homedir, self.gpgname, self.passphrase)

def signRpms(rpms, passphrase=None, public=None, secret=None, homedir=None,
             callback=RpmSignCallback(), working_dir=RPMSIGN_DIR):
  if callback: callback.start(len(rpms))
  working_dir = pps.path(working_dir)
  working_dir.mkdirs()
  for rpm in rpms:
    s = AddHandler(rpm, working_dir,
                   passphrase=passphrase, public=public,
                   secret=secret, homedir=homedir)
    try:
      try:
        s.open()
        s.run()
      except Exception, e:
        raise
    finally:
      s.close()
    if callback: callback.processed(rpm.basename)
  if working_dir == RPMSIGN_DIR:
    working_dir.rm(recursive=True, force=True)
  if callback: callback.end()

def verifyRpms(rpms, public=None, homedir=None,
               digest=True, signature=True, force=False,
               callback=RpmSignCallback(), working_dir=RPMSIGN_DIR):
  invalids = []
  if callback: callback.start(len(rpms))
  working_dir = pps.path(working_dir)
  working_dir.mkdirs()
  for rpm in rpms:
    v = VerifyHandler(rpm, working_dir,
                      public=public, homedir=homedir)
    try:
      try:
        v.open()
        v.run(digest=digest, signature=signature, force=force)
      except Exception, e:
        invalids.append(rpm)
    finally:
      v.close()
    if callback: callback.processed(rpm.basename)
  if working_dir == RPMSIGN_DIR:
    working_dir.rm(recursive=True, force=True)
  if callback: callback.end()
  return invalids

def deleteSignatures(rpms, callback=RpmSignCallback()):
  if callback: callback.start(len(rpms))
  for rpm in rpms:
    v = DeleteHandler(rpm)
    try:
      try:
        v.open()
        v.run()
      except Exception, e:
        raise
    finally:
      v.close()
      if callback: callback.processed(rpm.basename)

def verifyPassphrase(homedir, passphrase, gpgname=None):
  v = PassphraseVerifier(homedir, passphrase, gpgname)
  return v.check()

#--------- EXCEPTIONS/ERRORS ---------#
class IncorrectPassphraseError(Exception): pass
class MissingTagError(Exception): pass
class RpmSignatureInvalidError(Exception):
  def __init__(self, strerror, invalid_tags):
    self.strerror     = strerror
    self.invalid_tags = invalid_tags
  def __str__(self):
    return self.strerror

