#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
from openprovision.event import Event, CLASS_META

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['RpmbuildEvent'],
  description = 'modules that create system-specific RPMs',
)

class RpmbuildEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'rpmbuild',
      parentid = 'os',
      properties = CLASS_META,
      provides = ['rpmbuild-data', 'seckey', 'pubkey'],
      suppress_run_message = True
    )

    self.DATA = {
      'variables': [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.pubkey_text = PUBKEY
    self.seckey_text = SECKEY
    self.DATA['variables'].extend(['pubkey_text', 'seckey_text'])

    self.cvars['rpmbuild-data'] = {}

    self.pubkey = self.mddir/'RPM-GPG-KEY-openprovision'
    self.seckey = self.mddir/'RPM-GPG-KEY-openprovision-private'

  def run(self):
    self.io.clean_eventcache(all=True)
    self.pubkey.write_text(self.pubkey_text)
    self.seckey.write_text(self.seckey_text)
    self.DATA['output'].extend([self.pubkey, self.seckey])

  def apply(self):
    self.io.clean_eventcache()

    self.cvars['pubkey'] = self.pubkey
    self.cvars['seckey'] = self.seckey

  def verify_pubkey_exists(self):
    "pubkey exist"
    self.verifier.failUnlessExists(self.pubkey)

  def verify_seckey_exists(self):
    "seckey exist"
    self.verifier.failUnlessExists(self.seckey)

PUBKEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQGiBE1/0xURBACQJRY9A78vnkweEeUgRcqP32R81E4H3VdV1O5oa3qfw7niUrDV
bN2kwG+TvbJ9HvqcbutosO98zd32zAkK9+U8caO558ezimb+AdV4+j5Bwb3BT+RQ
ijMUb/V1kz7SuSmvIGiWGsAK3vl6oqdWaIxX1676tlKWpEoqZ7Xoa1ksMwCg8VTY
rHFG/DaqHoGWXGMvvhxwRWMEAIbN8pbAL219Ag4CzRH6mwq7BUhp8ZsCzb8HXguw
4IZJIiYONWOKaXgswMqw8MIkSsytP1Mnll6pnWytWhkPeV0gpZXB/AXt7spnf9oO
Kqj61GtvNxhSWyVfNu8oERq3+r8O65RE1b54cDcR0ruBJ+NXzpVlEb66ktEG9LDG
5iZcA/4hNVf1H3xoXj2Edb+vXQnAcYg5PaF/VX0kUj51wsswuwEWw80+fN/BjQ8F
83qQc0wbwHKXuHXti36H7kp6A9CqXcpVZxteVkF5qD5bBD3Mwe1OJ39PnpScNPz7
x+9WDg7BPTL+uV8pxzh84+ZY+7J5pVJZO7kfhyB1/b+NN2u+GLQ2U3lzdGVtU3R1
ZGlvIChkZWZhdWx0KSA8Y29udGFjdEByZW5kaXRpb25zb2Z0d2FyZS5jb20+iGAE
ExECACAFAk1/0xUCGwMGCwkIBwMCBBUCCAMEFgIDAQIeAQIXgAAKCRBJPcZmw2tS
vfPRAKCbcDmNPL3bIQSfJol+ba+yY649pQCgsjWeVeIKv1HpzcgS+8NH+3L9lqS5
Ag0ETX/THRAIALFSgBTWPi2vIjCwraod81rUBI3eZfvdwiur9XNXWceDTBBcQDJA
65mz7DhDthCuYclmRwW16jisU++Sox8lu2p/EF6qkxoCdP51wMIKWEgVdT34fvDL
2adkPsylURdE0lddYTWr0uV+zchJE6iOPveaMgaSga1vJgEH1kZqKl6GUE0tvaj+
YBBfn7YL1AiL9fIOqW/Fe7sTQE9uJfgtF/qlsQWjk95PzlWZ3zxEjER3dJ39n7l2
z7wV8D7uKMziLg3T1K/dhXAu3j5GKoIJTg6tDByAvTnvZrH9fanZ0BII7PAhcd3X
8N1/vXQJFU7afIrkLRBLpsOt9W4m87/ruesAAwYH/3Mz2a9CY/DMaMe41jQUVN2z
9ImaipTIvxAzfKnfoQprw6eX/y0PY+widMZAhfNT+hCVgQy+4hQ3GnHXSwxSwGyp
dRIVRUI/yHWSde9yuEeW4BJaRCTtl5tCBMlckzSYUYFonBFILb5DSeCyX9dzIDSA
kJZ32Gs/nkg8vlHNOc+sxfHtreoZ3dt3guzUTp2pH+Lq/ugxXotmt88HASRZdZjM
71DlerOAicXjS3oXIuTMyse0z74E9jQRI1/5cl5J6RDYYpC0pVLwvWWLjSBqK7+7
z+RUEusrZkFmbHJzZ+5OSREozZFKFUEfo+xJEdjqXfK+r57ZX9S0Xui4HC+4U02I
SQQYEQIACQUCTX/THQIbDAAKCRBJPcZmw2tSvZBHAJ4k/u19038qysemGjjd+bck
KZusQgCgwE/h4YciTPrUdpXk/Ike9CdKSCc=
=yAM/
-----END PGP PUBLIC KEY BLOCK-----"""


SECKEY ="""-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQG7BE1/0xURBACQJRY9A78vnkweEeUgRcqP32R81E4H3VdV1O5oa3qfw7niUrDV
bN2kwG+TvbJ9HvqcbutosO98zd32zAkK9+U8caO558ezimb+AdV4+j5Bwb3BT+RQ
ijMUb/V1kz7SuSmvIGiWGsAK3vl6oqdWaIxX1676tlKWpEoqZ7Xoa1ksMwCg8VTY
rHFG/DaqHoGWXGMvvhxwRWMEAIbN8pbAL219Ag4CzRH6mwq7BUhp8ZsCzb8HXguw
4IZJIiYONWOKaXgswMqw8MIkSsytP1Mnll6pnWytWhkPeV0gpZXB/AXt7spnf9oO
Kqj61GtvNxhSWyVfNu8oERq3+r8O65RE1b54cDcR0ruBJ+NXzpVlEb66ktEG9LDG
5iZcA/4hNVf1H3xoXj2Edb+vXQnAcYg5PaF/VX0kUj51wsswuwEWw80+fN/BjQ8F
83qQc0wbwHKXuHXti36H7kp6A9CqXcpVZxteVkF5qD5bBD3Mwe1OJ39PnpScNPz7
x+9WDg7BPTL+uV8pxzh84+ZY+7J5pVJZO7kfhyB1/b+NN2u+GAAAoKauMH2lDwCB
qk1F5jFVjTCVZ6LaCbO0NlN5c3RlbVN0dWRpbyAoZGVmYXVsdCkgPGNvbnRhY3RA
cmVuZGl0aW9uc29mdHdhcmUuY29tPohgBBMRAgAgBQJNf9MVAhsDBgsJCAcDAgQV
AggDBBYCAwECHgECF4AACgkQST3GZsNrUr3z0QCgm3A5jTy92yEEnyaJfm2vsmOu
PaUAoLI1nlXiCr9R6c3IEvvDR/ty/ZaknQI9BE1/0x0QCACxUoAU1j4tryIwsK2q
HfNa1ASN3mX73cIrq/VzV1nHg0wQXEAyQOuZs+w4Q7YQrmHJZkcFteo4rFPvkqMf
JbtqfxBeqpMaAnT+dcDCClhIFXU9+H7wy9mnZD7MpVEXRNJXXWE1q9Llfs3ISROo
jj73mjIGkoGtbyYBB9ZGaipehlBNLb2o/mAQX5+2C9QIi/XyDqlvxXu7E0BPbiX4
LRf6pbEFo5PeT85Vmd88RIxEd3Sd/Z+5ds+8FfA+7ijM4i4N09Sv3YVwLt4+RiqC
CU4OrQwcgL0572ax/X2p2dASCOzwIXHd1/Ddf710CRVO2nyK5C0QS6bDrfVuJvO/
67nrAAMGB/9zM9mvQmPwzGjHuNY0FFTds/SJmoqUyL8QM3yp36EKa8Onl/8tD2Ps
InTGQIXzU/oQlYEMvuIUNxpx10sMUsBsqXUSFUVCP8h1knXvcrhHluASWkQk7Zeb
QgTJXJM0mFGBaJwRSC2+Q0ngsl/XcyA0gJCWd9hrP55IPL5RzTnPrMXx7a3qGd3b
d4Ls1E6dqR/i6v7oMV6LZrfPBwEkWXWYzO9Q5XqzgInF40t6FyLkzMrHtM++BPY0
ESNf+XJeSekQ2GKQtKVS8L1li40gaiu/u8/kVBLrK2ZBZmxyc2fuTkkRKM2RShVB
H6PsSRHY6l3yvq+e2V/UtF7ouBwvuFNNAAFUDNI0RaMS9q+00BSIvnZhOFlVC/A4
1h/mNQ0bt5njCbAK3qRXa8QcNah1UxPLiEkEGBECAAkFAk1/0x0CGwwACgkQST3G
ZsNrUr2QRwCdHUhS1k6WvjMkaoJ90E/KFiPdKRgAoKFOArbX2eNsTFADcS3wCJX+
mIJX
=q1x+
-----END PGP PRIVATE KEY BLOCK-----"""
