#
# Copyright (c) 2012
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
import unittest

from centosstudio.errors   import CentOSStudioError
from centosstudio.util     import pps 
from centosstudio.util     import rxml

from cstest       import EventTestCase, ModuleTestSuite
from cstest.core  import make_core_suite

PUBKEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQGiBE7iLHkRBACbHdCzgO5Jac4LRbQwKoX+1ltYHrvvc/WsnhuPN5HXhvkPTA+/
rbsCxm8oqzP5puu7rimcnZkHN7pN/8uKj5Vd7EbaVNSWUg7rfhDlxg/KxDAnXPuI
JBhER92JfU0y5D1SOb4SmSJ32E79zrDVFt0XFlOP6biwFS/RGHRJxzjGlwCgnOcN
AYveV6pXd8Ec9OX6Lea+46sD/289sU6VeSg9KruXM67LjDei/P8aDAGsABdhq57F
L7eOcWewZ0UZDQh1zSB+r0DoWF6rpj7oQ/yRWoHWXgFfUX8tL5AV7HuNmsxAfvy/
/xBs8YVgBxieeiWrBGxcBQRdXZDSSOz2WYExir5y4/ehn3Upn5WKeUqkP5uAsQkB
XFOyA/wOOd4azDKd0uouLgluJbqYMSlRDoigNbHWVPAM3PvZdusgzP2JO91IxCHD
JeCpZWgfN29g8py66PkXg7EfsisQqVO3/42me96Tqb/77Y8kSbubWQ4uVQd5YB8z
0sGT71S6NrAnhqyqs7toMjUGO5JuMfnP/hgITk967nV5jZowX7QQdGVzdCBzaWdu
aW5nIGtleYhgBBMRAgAgBQJO4ix5AhsjBgsJCAcDAgQVAggDBBYCAwECHgECF4AA
CgkQyubdJwqXVrONfQCfUS5Qb14tm2ADjxLoZRuYtEpn9WsAoJwnvOfR7XE/Qjqq
s6JooAwdguR6uQENBE7iLHoQBACvveBthapADqBic6ijcQbt1Hb6E/9HAwxubRpj
yl0g8uC1ZxfcQKJ1GT983Bx/okvP73olKOxV1xnlpT7DV+6EYucIGVyW55mrxI3H
P7o1Ox1wvh7fP/pm6Yf//OLF9lFUh3h0/mYziqAaf0L/Vm3aWu9Hl02IJToVifAC
GemE7wADBQQAovTMQ5k8RG1k5jCUqRV280FKInE24M/75YbNXwdTkGfp9pl1ceNJ
1vhlZg3JuHnZ0uw0p3la7WUCut0afy7vCRQPD4g8E57vfBFzOpiifXbEP5VHa37e
hY3hoknv0N3UP7EjWxUoifSi1VsV8WMHcJVxKgu6//oXsHQ6GSypR1aISQQYEQIA
CQUCTuIsegIbDAAKCRDK5t0nCpdWs0DuAKCXthQjeX5H4DL9sZUkxk+k4wiHtgCf
TBefZqqYtL+kacCEgCIYH2Fhm0I=
=9xNj
-----END PGP PUBLIC KEY BLOCK-----"""

SECKEY = """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQG7BE7iLHkRBACbHdCzgO5Jac4LRbQwKoX+1ltYHrvvc/WsnhuPN5HXhvkPTA+/
rbsCxm8oqzP5puu7rimcnZkHN7pN/8uKj5Vd7EbaVNSWUg7rfhDlxg/KxDAnXPuI
JBhER92JfU0y5D1SOb4SmSJ32E79zrDVFt0XFlOP6biwFS/RGHRJxzjGlwCgnOcN
AYveV6pXd8Ec9OX6Lea+46sD/289sU6VeSg9KruXM67LjDei/P8aDAGsABdhq57F
L7eOcWewZ0UZDQh1zSB+r0DoWF6rpj7oQ/yRWoHWXgFfUX8tL5AV7HuNmsxAfvy/
/xBs8YVgBxieeiWrBGxcBQRdXZDSSOz2WYExir5y4/ehn3Upn5WKeUqkP5uAsQkB
XFOyA/wOOd4azDKd0uouLgluJbqYMSlRDoigNbHWVPAM3PvZdusgzP2JO91IxCHD
JeCpZWgfN29g8py66PkXg7EfsisQqVO3/42me96Tqb/77Y8kSbubWQ4uVQd5YB8z
0sGT71S6NrAnhqyqs7toMjUGO5JuMfnP/hgITk967nV5jZowXwAAnA12xL8lKygY
avXfoZC4hAHepi0VCaS0EHRlc3Qgc2lnbmluZyBrZXmIYAQTEQIAIAUCTuIseQIb
IwYLCQgHAwIEFQIIAwQWAgMBAh4BAheAAAoJEMrm3ScKl1azjX0An1EuUG9eLZtg
A48S6GUbmLRKZ/VrAKCcJ7zn0e1xP0I6qrOiaKAMHYLkep0BMgRO4ix6EAQAr73g
bYWqQA6gYnOoo3EG7dR2+hP/RwMMbm0aY8pdIPLgtWcX3ECidRk/fNwcf6JLz+96
JSjsVdcZ5aU+w1fuhGLnCBlclueZq8SNxz+6NTsdcL4e3z/6ZumH//zixfZRVId4
dP5mM4qgGn9C/1Zt2lrvR5dNiCU6FYnwAhnphO8AAwUEAKL0zEOZPERtZOYwlKkV
dvNBSiJxNuDP++WGzV8HU5Bn6faZdXHjSdb4ZWYNybh52dLsNKd5Wu1lArrdGn8u
7wkUDw+IPBOe73wRczqYon12xD+VR2t+3oWN4aJJ79Dd1D+xI1sVKIn0otVbFfFj
B3CVcSoLuv/6F7B0OhksqUdWAAD5AfL1s+wz653stZOKhxMX1S9gbq4A9nQesx45
o2iyjegR7ohJBBgRAgAJBQJO4ix6AhsMAAoJEMrm3ScKl1azQO4An3vR7ZjQ80tD
MkKc5Q91TmwC5A7jAJ9jvRPHOVwYC+sHFL4mOt/9XVaFdg==
=k9wN
-----END PGP PRIVATE KEY BLOCK-----"""

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

PASSPHRASE = "The quick brown fox jumped over the lazy dog."


class GpgsignTestCase(EventTestCase):
  moduleid = 'gpgsign'
  eventid  = 'gpgsign'
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
    self.failUnlessRaises(CentOSStudioError, self.event)
  
class Test_SigningKeysPassphrase(GpgsignTestCase):
  "Passphrase used if provided"
  _conf = """
  <gpgsign>
    <public>%s</public>
    <secret>%s</secret>
    <passphrase>%s</passphrase>
  </gpgsign>
  """ % (PASSPUB, PASSSEC, PASSPHRASE)

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
  
class Test_GeneratesSigningKeys(GpgsignTestCase):
  "Generates signing keys"
  _conf = """<rpmbuild/>"""

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    xpath = '/*/%s' % self.event.id
    datfile = rxml.datfile.parse(self.event._config.file)
    self.failUnless(
      datfile.get('%s/pubkey' % xpath, None) is not None and
      datfile.get('%s/seckey' % xpath, None) is not None) 

class Test_ReadsKeysFromDatfile(GpgsignTestCase):
  "Keys read from datfile"
  _conf = """<rpmbuild/>"""

  def runTest(self):
    xpath = '/*/%s' % self.event.id
    datfile = rxml.datfile.parse(self.event._config.file)
    pubtext = datfile.get('%s/pubkey' % xpath, None)
    sectext = datfile.get('%s/seckey' % xpath, None)

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
    datfile = rxml.datfile.parse(self.event._config.file)
    self.failUnless(
      datfile.get('%s/pubkey' % xpath, None) is None and 
      datfile.get('%s/seckey' % xpath, None) is None)


def make_suite(distro, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('rpmbuild')

  suite.addTest(make_core_suite(GpgsignTestCase, distro, version, arch))
  suite.addTest(Test_SigningKeysValid(distro, version, arch))
  suite.addTest(Test_SigningKeysPassphrase(distro, version, arch))
  suite.addTest(Test_GeneratesSigningKeys(distro, version, arch))
  suite.addTest(Test_ReadsKeysFromDatfile(distro, version, arch))
  suite.addTest(Test_KeysRemovedFromDatfile(distro, version, arch))

  return suite
