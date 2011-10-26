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
gpgparse.py

Python representation of gpg key information as reported by gpg.

Parses the output of gpg --list-(secret-)keys --with-colons --fixed-list-mode
"""

import re
import time

PRINTF_REGEX = re.compile('%{[^}]*}')

#------ CONSTANTS ------#
FIELD_TYPE   = 0
FIELD_TRUST  = 1
FIELD_LENGTH = 2
FIELD_ALGO   = 3
FIELD_KEYID  = 4
FIELD_CTIME  = 5 # creation date
FIELD_ETIME  = 6 # expire date
FIELD_SERIAL = 7
FIELD_OTRUST = 8 # owner trust
FIELD_UID    = 9 # user id
FIELD_SCLASS = 10 # signature class
FIELD_CPBLS  = 11 # capabilities
FIELD_FPR    = 12 # fingerprint
FIELD_FLAG   = 13
FIELD_TKSN   = 14

KEY_TYPE_PUBLIC  = 0
KEY_TYPE_SECRET  = 1
KEY_TYPE_PRIMARY = 00
KEY_TYPE_SUBKEY  = 10

TRUST_NEW       = 'o'
TRUST_INVALID   = 'i'
TRUST_DISABLED  = 'd' # deprecated
TRUST_REVOKED   = 'r'
TRUST_EXPIRED   = 'e'
TRUST_UNKNOWN   = '-'
TRUST_UNDEFINED = 'q'
TRUST_NO_TRUST  = 'n'
TRUST_MARGINAL_TRUST   = 'm'
TRUST_FULL_TRUST       = 'f'
TRUST_ULTIMATELY_TRUST = 't'

CAPABLE_ENC  = 'e'
CAPABLE_SIGN = 's'
CAPABLE_CERT = 'c'
CAPABLE_AUTH = 'a'
CAPABLE_ENC_USABLE  = 'E'
CAPABLE_SIGN_USABLE = 'S'
CAPABLE_CERT_USABLE = 'C'
CAPABLE_AUTH_USABLE = 'A'
CAPABLE_DISABLED = 'D'

CIPHER_ALGO_NONE     = 0
CIPHER_ALGO_IDEA     = 1
CIPHER_ALGO_3DES     = 2
CIPHER_ALGO_CASTS    = 3
CIPHER_ALGO_BLOWFISH = 4
# 5 and 6 reserved
CIPHER_ALGO_AES      = 7
CIPHER_ALGO_AES192   = 8
CIPHER_ALGO_AES256   = 9
CIPHER_ALGO_TWOFISH  = 10
CIPHER_ALGO_DUMMY    = 110

PUBKEY_ALGO_RSA       = 1
PUBKEY_ALGO_RSA_E     = 2
PUBKEY_ALGO_RSA_S     = 3
PUBKEY_ALGO_ELGAMAL_E = 16
PUBKEY_ALGO_DSA       = 17
PUBKEY_ALGO_ELGAMAL   = 20

PUBKEY_USAGE_SIG     = 1
PUBKEY_USAGE_ENC     = 2
PUBKEY_USAGE_CERT    = 4
PUBKEY_USAGE_AUTH    = 8
PUBKEY_USAGE_UNKNOWN = 128

DIGEST_ALGO_MD5    = 1
DIGEST_ALGO_SHA1   = 2
DIGEST_ALGO_RMD160 = 3
DIGEST_ALGO_SHA256 = 8
DIGEST_ALGO_SHA384 = 9
DIGEST_ALGO_SHA512 = 10
DIGEST_ALGO_SHA224 = 11

COMPRESS_ALGO_NONE  = 0
COMPRESS_ALGO_ZIP   = 1
COMPRESS_ALGO_ZLIB  = 2
COMPRESS_ALGO_BZIP2 = 3

#------ CLASSES ------#
class Key:
  """
  Class representing a GPG key.  It has a number of fields representing the various
  properties a GPG key can have.  See GPG's documentation about keys to find out
  the meaning of the fields.
  """
  def __init__(self, type, trust, length, algorithm, keyid, ctime, expire,
               sigclass, capabilities):
    self.type = int(type)
    self.trust = trust
    self.length = int(length)
    self.algorithm = int(algorithm)
    self.keyid = keyid
    self.ctime = int(ctime)
    if expire is not None:
      self.expire = int(expire)
    else:
      self.expire = None
    self.sigclass = sigclass
    self.capabilities = capabilities

    self.issubkey = 10 & self.type
    self.issecretkey = 01 & self.type

    self.userid = None
    self.subkey = None

  def hascapability(self, c):
    "Return True if the capability c is in this key's cability list"
    return c in self.capabilities

  def expired(self):
    "Return True if this key has expired"
    if self.expire is not None:
      return time.time() > self.expire
    else:
      return False

  def printf(self, format):
    """
    Return a formatted string representation of this key.  Attributes are accessed
    by enclosing their attribute name in '%{' and '}'; string patterns matching this
    format are replaced with the string representation of that attribute.  If a given
    attribute does not exist, raises a ValueError.
    """
    toreplace = PRINTF_REGEX.findall(format)
    for r in toreplace:
      var = r[2:-1] # remove '%{' and '}'
      if not hasattr(self, var):
        raise ValueError, "Invalid format value '%s'" % r
      format = format.replace(r, str(getattr(self, var)))
    return format

  def __str__(self):
    "Print out the key in the same format used by GPG"
    if self.issubkey:
      type = 'sub'; ind = 'g'
    else:
      type = 'pub'; ind = 'D'
    ctime = time.strftime('%Y-%m-%d', time.gmtime(self.ctime))
    if self.userid is not None:
      userstr = '\n' + str(self.userid)
    else:
      userstr = ''
    if self.subkey is not None:
      subkeystr = '\n' + str(self.subkey)
    else:
      subkeystr = ''

    return '%s\t%s%s/%s\t%s%s%s' % \
      (type, self.length, ind, self.keyid[:-8], ctime, userstr, subkeystr)


class UID:
  "Class representing a UID (user id) of a GPG key"
  def __init__(self, trust, ctime, sn, uid):
    self.trust = trust
    self.ctime = ctime
    self.sn = sn
    self.uid = uid

  def __str__(self):
    return 'uid\t\t\t%s' % self.uid

# mapping of record types to classes
RECTYPE_MAP = {
  #'tru': ,
  'pub': Key,
  'uid': UID,
  'sub': Key,
  'sec': Key,
  'ssb': Key,
  #'crt': ,
  #'crs': ,
  #'uat': ,
  #'sig': ,
  #'rev': ,
  #'fpr': ,
  #'pkd': ,
  #'grp': ,
  #'rvk': ,
  #'spk': ,
}


def parsekeys(string):
  """
  Parse a string, attempting to resolve it into a list of Key objects.

  Accepts either a string with newline characters or a list of newline-separated
  lines.  The standard way to generate the output for this function is to run
  the following command:

    gpg --homedir <homedir> --with-colons --fixed-width-mode --list(-secret)-keys

  """
  if isinstance(string, str):
    string = string.split('\n')

  keys = []

  i = 0
  currkey = None
  while i < len(string):
    line = string[i]
    struct = line.split(':')
    if struct[0] == 'pub':
      currkey = PublicKey(struct)
      keys.append(currkey)
    else:
      if currkey is None:
        i += 1; continue
      else:
        if struct[0] == 'sub':
          currkey.subkey = SubKey(struct)
        elif struct[0] == 'uid':
          currkey.userid = UserID(struct)
    i += 1


  return keys

#------ FACTORY FUNCTIONS ------#
def PublicKey(l):
  return Key(type      = KEY_TYPE_PUBLIC | KEY_TYPE_PRIMARY,
             trust     = l[FIELD_TRUST],
             length    = l[FIELD_LENGTH],
             algorithm = l[FIELD_ALGO],
             keyid     = l[FIELD_KEYID],
             ctime     = l[FIELD_CTIME],
             expire    = l[FIELD_ETIME] or None,
             sigclass  = l[FIELD_SCLASS] or None,
             capabilities = l[FIELD_CPBLS])

def SubKey(l):
  return Key(type      = KEY_TYPE_PUBLIC | KEY_TYPE_SUBKEY,
             trust     = l[FIELD_TRUST],
             length    = l[FIELD_LENGTH],
             algorithm = l[FIELD_ALGO],
             keyid     = l[FIELD_KEYID],
             ctime     = l[FIELD_CTIME],
             expire    = l[FIELD_ETIME] or None,
             sigclass  = l[FIELD_SCLASS] or None,
             capabilities = l[FIELD_CPBLS])

def UserID(l):
  return UID(trust  = l[FIELD_TRUST],
             ctime  = l[FIELD_CTIME],
             sn     = l[FIELD_SERIAL],
             uid    = l[FIELD_UID])
