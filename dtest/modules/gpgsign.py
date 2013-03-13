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
import unittest

from deploy.errors   import DeployError
from deploy.util     import pps 
from deploy.util     import rxml

from dtest       import EventTestCase, ModuleTestSuite
from dtest.core  import make_core_suite

from dtest.mixins.rpmbuild import PUBKEY, SECKEY

PASSPUB = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQGiBE7lgboRBACnvq96GHE/tnXD5T035xAoDpVHs1GgSj2hsOkviDq+RhzphQ3v
0j06BCPRxqBL6jDO7riiHaxgkI9dlAP2lK0+zFH5k3g0KeYT2EyLRo3E5OKqLW/f
FFxuynVUnNl5GO7yyf0/Z+XQUMZfNr7nwXj602zLcBvs0ajqJlkOY2R3CwCgvKXy
dPMKrMgQrz7jgzDnLmPOGpsD/jXIzpoojosXeIXIu+6LQc2SkmgbSGcj5UoYw70p
5dC5Vp71G0DWUhXwq62plGvjng0LiW5dbymw8b4Pc6l15vBEGkcTQQYJtJEm+ab8
vquqYYHZzYcF29YT78Rys7oUOGbWOZCxGLGLhshk7v856YsBR8Z7m5Z64enc0xmj
jqOWA/9eu915eOI8SF4fohbo2Cm4mk4nda4ozouTdey7ulNvvIjZTB5DyaREDtll
7mAI8C7lt8EkgvJcq1h6PlMoh8Y1fSQVkFAHbCo80Y9vCTKcm8SmAePIJdloeiFN
A6hcj4GqdAVROT4fOJXC2yg4TUrBRlQYuDaFdsoWZLt/k9EnZ7QgdGVzdCBzaWdu
aW5nIGtleSB3aXRoIHBhc3NwaHJhc2WIYAQTEQIAIAUCTuWBugIbIwYLCQgHAwIE
FQIIAwQWAgMBAh4BAheAAAoJEHOQg+8FJLzD0NsAoIzs8IJ/hwDtN7+QKgaHnjEe
5vFUAJ4wVN5WHR3oa0O0Kbyrk1mFoXZpp7kBDQRO5YG7EAQAlPZuSJbToa0SPKqp
HKIMttZ84coImZjM3RhchU/GrofRuF2xFW4ADFJlQZKgdZyK6p24W1u35ahhItQe
PQ6L+laxSda/v5aCCpLPjaAG/MMbY0wE91GocDwDEtHeMNur2JlOeSNaaWwCeW+m
YqGsnPdp9O7psGRszGGOHDRKrzcABAsD/0/BC+lF+8TuruRA4qaI8hyxOdLkWr4R
XVqODYN6iWzKy+uIgdtQAassdrL5llDIwe1F5VyqF0c8vq9QxXaX0UpdMR8PCqNn
h5PL7DLRZ1buW9LRVFoQMHcRJWfUHTnYuuECl6GVscQFAP64W9zHa/6XPJW/qR5L
ws6twIqIwlOBiEkEGBECAAkFAk7lgbsCGwwACgkQc5CD7wUkvMPQeQCeLsseGp56
mRGmCU/C+vso8VYkGDYAoIBQ9Mf+1NmAld+uicbqivaYD8hL
=//E+
-----END PGP PUBLIC KEY BLOCK-----"""

PASSSEC = """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQHhBE7lgboRBACnvq96GHE/tnXD5T035xAoDpVHs1GgSj2hsOkviDq+RhzphQ3v
0j06BCPRxqBL6jDO7riiHaxgkI9dlAP2lK0+zFH5k3g0KeYT2EyLRo3E5OKqLW/f
FFxuynVUnNl5GO7yyf0/Z+XQUMZfNr7nwXj602zLcBvs0ajqJlkOY2R3CwCgvKXy
dPMKrMgQrz7jgzDnLmPOGpsD/jXIzpoojosXeIXIu+6LQc2SkmgbSGcj5UoYw70p
5dC5Vp71G0DWUhXwq62plGvjng0LiW5dbymw8b4Pc6l15vBEGkcTQQYJtJEm+ab8
vquqYYHZzYcF29YT78Rys7oUOGbWOZCxGLGLhshk7v856YsBR8Z7m5Z64enc0xmj
jqOWA/9eu915eOI8SF4fohbo2Cm4mk4nda4ozouTdey7ulNvvIjZTB5DyaREDtll
7mAI8C7lt8EkgvJcq1h6PlMoh8Y1fSQVkFAHbCo80Y9vCTKcm8SmAePIJdloeiFN
A6hcj4GqdAVROT4fOJXC2yg4TUrBRlQYuDaFdsoWZLt/k9EnZ/4DAwILVMIXaluF
U2C8Rk8mnXh84jH15VrcI0rfeI8lOMZKNxCr1zVp8fFAY3FUOcI8OTfytIt2ujvl
CQcCybQgdGVzdCBzaWduaW5nIGtleSB3aXRoIHBhc3NwaHJhc2WIYAQTEQIAIAUC
TuWBugIbIwYLCQgHAwIEFQIIAwQWAgMBAh4BAheAAAoJEHOQg+8FJLzD0NsAoIzs
8IJ/hwDtN7+QKgaHnjEe5vFUAJ4wVN5WHR3oa0O0Kbyrk1mFoXZpp50BWARO5YG7
EAQAlPZuSJbToa0SPKqpHKIMttZ84coImZjM3RhchU/GrofRuF2xFW4ADFJlQZKg
dZyK6p24W1u35ahhItQePQ6L+laxSda/v5aCCpLPjaAG/MMbY0wE91GocDwDEtHe
MNur2JlOeSNaaWwCeW+mYqGsnPdp9O7psGRszGGOHDRKrzcABAsD/0/BC+lF+8Tu
ruRA4qaI8hyxOdLkWr4RXVqODYN6iWzKy+uIgdtQAassdrL5llDIwe1F5VyqF0c8
vq9QxXaX0UpdMR8PCqNnh5PL7DLRZ1buW9LRVFoQMHcRJWfUHTnYuuECl6GVscQF
AP64W9zHa/6XPJW/qR5Lws6twIqIwlOB/gMDAgtUwhdqW4VTYBD7dVNR/Q85SODq
pmFkVxnj7uI6X3CSrX7nW1dJoSRQdg7Ak86g/z6HdDxxjr9T5s5JJkXU1h6rIcJe
2Z6miEkEGBECAAkFAk7lgbsCGwwACgkQc5CD7wUkvMPQeQCgtLE1GYE+fV/ck4Pf
28sJonN3QlAAnAi1vRYxQxb0OiVewcW3QWy4yKxc
=1hjY
-----END PGP PRIVATE KEY BLOCK-----"""

# Correct passphrase
PASSGOOD = "The quick brown fox jumped over the lazy dog."

# Bad passphrase
PASSBAD = "bad"

class GpgsignTestCase(EventTestCase):
  moduleid = 'gpgsign'
  eventid  = 'gpgsign'
  _mode = 'package'
  conf = """<gpgsign enabled="true">
      <public>%s</public>
      <secret>%s</secret>
  </gpgsign>""" % (PUBKEY, SECKEY)

class Test_SigningKeysValid(GpgsignTestCase):
  "Provided signing keys are valid"
  _conf = """
  <gpgsign>
    <public>invalid</public>
    <secret>invalid</secret>
  </gpgsign>
  """

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)
  
class Test_GeneratesSigningKeys(GpgsignTestCase):
  "Generates signing keys"
  _conf = """<rpmbuild/>"""

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    xpath = '/*/%s' % self.event.id
    datfile = self.event.parse_datfile()
    self.failUnless(
      datfile.getxpath('%s/pubkey' % xpath, None) is not None and
      datfile.getxpath('%s/seckey' % xpath, None) is not None) 

class Test_ReadsKeysFromDatfile(GpgsignTestCase):
  "Keys read from datfile"
  _conf = """<rpmbuild/>"""

  def runTest(self):
    xpath = '/*/%s' % self.event.id
    datfile = self.event.parse_datfile()
    pubtext = datfile.getxpath('%s/pubkey' % xpath, None)
    sectext = datfile.getxpath('%s/seckey' % xpath, None)

    self.tb.dispatch.execute(until=self.event)

    self.failUnless(pubtext is not None and 
                    self.event.pubkey.read_text() != pubtext and
                    sectext is not None and
                    self.event.seckey.read_text() != sectext)

class Test_KeysRemovedFromDatfile(GpgsignTestCase):
  "Keys removed from datfile"
  _conf = """
    <gpgsign>
      <public>%s</public>
      <secret>%s</secret>
    </gpgsign>
  """ % (PUBKEY, SECKEY)

  def runTest(self):
    xpath = '/*/%s/' % self.event.id
    self.tb.dispatch.execute(until=self.event)
    datfile = self.event.parse_datfile()
    self.failUnless(
      datfile.getxpath('%s/pubkey' % xpath, None) is None and 
      datfile.getxpath('%s/seckey' % xpath, None) is None)

class Test_SigningKeysGoodPassphrase(GpgsignTestCase):
  "Success on good passphrase"
  eventid  = 'release-rpm' # using release rpm to test passphrase

  _conf = ["""
  <gpgsign>
    <public>%s</public>
    <secret>%s</secret>
    <passphrase>%s</passphrase>
  </gpgsign>
  """ % (PASSPUB, PASSSEC, PASSGOOD),]

  def runTest(self):
    # execute until release-rpm to ensure signing occurs without error
    self.tb.dispatch.execute(until=self.event)
  
class Test_SigningKeysBadPassphrase(GpgsignTestCase):
  "Error on bad passphrase"
  eventid  = 'release-rpm' # using release rpm to test passphrase

  _conf = ["""
  <gpgsign>
    <public>%s</public>
    <secret>%s</secret>
    <passphrase>%s</passphrase>
  </gpgsign>
  """ % (PASSPUB, PASSSEC, PASSBAD),]

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('rpmbuild')

  suite.addTest(make_core_suite(GpgsignTestCase, os, version, arch))
  suite.addTest(Test_SigningKeysValid(os, version, arch))
  suite.addTest(Test_GeneratesSigningKeys(os, version, arch))
  suite.addTest(Test_ReadsKeysFromDatfile(os, version, arch))
  suite.addTest(Test_KeysRemovedFromDatfile(os, version, arch))
  suite.addTest(Test_SigningKeysGoodPassphrase(os, version, arch))
  suite.addTest(Test_SigningKeysBadPassphrase(os, version, arch))

  return suite
