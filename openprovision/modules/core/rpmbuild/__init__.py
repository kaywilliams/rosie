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

mQGiBE5AmpMRBACrSjfekSG5HJfVZ/emySv82sB1HEhRNkPRWfd/G4yNqRJu88mX
yxF9vXnhXYyDkamnkcoG7Ycok/SqeIN0No9v1EX0YdKxE7ItVq/QzOL8WX937bZ1
639xJQIug1chbNlYPV4kXEVWSM2QrYRwYG+1iNCuH0tKDr/wKnDWPQzvJwCgmde+
QEE1E7YVvK9EpzEhqb7UoFkD/jk1sQmqD6pxs9d/Ihryv9ZLT8MLpzMpevZTOWvC
+vmhctEMdrBHE4zd9MDCaRU0Yhz8I0GAVWdsOLS2J0o50XdteD/1KrOUQ6nr6nN3
5uZqtYmjvIVz8jpQz1STpK+ee+tDP2uGMAhxk3mXXOCTiozM/0z3pMyZFE+qzMFY
yKyFA/0fKhtB5hnN+1PRT6MTlBaydk0ENdKNzeZtH6Km/e215iXLH9jEy0aN1Ncy
ZdvWMT9OrMqwFdl1TQw9IzLr2LA5xgdmPlI5r0rDpLrzxxRjJyrsZzNVXJEmd3Ro
En1oAOkxiR543iFux7BJkZ2elXM4mQLsuHoPc1Kk9sArzVoMFLQxT3BlblByb3Zp
c2lvbiBTaWduaW5nIEtleSA8a2V5QG9wZW5wcm92aXNpb24uY29tPohgBBMRAgAg
BQJOQJqTAhsDBgsJCAcDAgQVAggDBBYCAwECHgECF4AACgkQuF9imeVXQZnxSQCf
eWRwxvCV1j/yW8XrbIh9GweJhx4An2SmzKQFxTiFqL5CPGyCbBT460DPuQENBE5A
mpQQBADjRo7IHrfmx42MS2LsGTb7FJ706HqxYdkJkYsPpB85I4dcaAl4L8fNjw1v
1mSa7nvN8fHpEfu7RNF5JBHuYOblays/Nr5uRpPXpHzTLezXkMfYltEbY8q/1opN
5zN71KwCZTY40G15cDYUe33pgXMqMZ4kS89ZU9iuihz+j9Z5MwADBQQAwUmV1/Ci
RsF3LgaH3pwdxDvhhVlmr+9i/LW5v7NDvFIGew/rWjKEdCGyUPYZf1WCURvm1ffF
S1tZR56yfJ6DSukWjKxdM+KfH5Bzf1XWWWIHNxNIquZy0r7z9xUVjHYrG2ZTnSIa
W5ZkqyhaPF4g+rCXoCfcyZYz1mY7z5/TEqaISQQYEQIACQUCTkCalAIbDAAKCRC4
X2KZ5VdBmfJoAKCIbjiW3/M6VQ/LonzIK2sYbdpm5ACfaxLB3AUfwzrzuM0/b8jt
MTWUcB0=
=q2s4
-----END PGP PUBLIC KEY BLOCK-----"""


SECKEY ="""-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQG7BE5AmpMRBACrSjfekSG5HJfVZ/emySv82sB1HEhRNkPRWfd/G4yNqRJu88mX
yxF9vXnhXYyDkamnkcoG7Ycok/SqeIN0No9v1EX0YdKxE7ItVq/QzOL8WX937bZ1
639xJQIug1chbNlYPV4kXEVWSM2QrYRwYG+1iNCuH0tKDr/wKnDWPQzvJwCgmde+
QEE1E7YVvK9EpzEhqb7UoFkD/jk1sQmqD6pxs9d/Ihryv9ZLT8MLpzMpevZTOWvC
+vmhctEMdrBHE4zd9MDCaRU0Yhz8I0GAVWdsOLS2J0o50XdteD/1KrOUQ6nr6nN3
5uZqtYmjvIVz8jpQz1STpK+ee+tDP2uGMAhxk3mXXOCTiozM/0z3pMyZFE+qzMFY
yKyFA/0fKhtB5hnN+1PRT6MTlBaydk0ENdKNzeZtH6Km/e215iXLH9jEy0aN1Ncy
ZdvWMT9OrMqwFdl1TQw9IzLr2LA5xgdmPlI5r0rDpLrzxxRjJyrsZzNVXJEmd3Ro
En1oAOkxiR543iFux7BJkZ2elXM4mQLsuHoPc1Kk9sArzVoMFAAAnivEOCtTxcf1
h55KdFtaxMynqyFWCrW0MU9wZW5Qcm92aXNpb24gU2lnbmluZyBLZXkgPGtleUBv
cGVucHJvdmlzaW9uLmNvbT6IYAQTEQIAIAUCTkCakwIbAwYLCQgHAwIEFQIIAwQW
AgMBAh4BAheAAAoJELhfYpnlV0GZ8UkAn3lkcMbwldY/8lvF62yIfRsHiYceAJ9k
psykBcU4hai+QjxsgmwU+OtAz50BMgROQJqUEAQA40aOyB635seNjEti7Bk2+xSe
9Oh6sWHZCZGLD6QfOSOHXGgJeC/HzY8Nb9Zkmu57zfHx6RH7u0TReSQR7mDm5Wsr
Pza+bkaT16R80y3s15DH2JbRG2PKv9aKTecze9SsAmU2ONBteXA2FHt96YFzKjGe
JEvPWVPYrooc/o/WeTMAAwUEAMFJldfwokbBdy4Gh96cHcQ74YVZZq/vYvy1ub+z
Q7xSBnsP61oyhHQhslD2GX9VglEb5tX3xUtbWUeesnyeg0rpFoysXTPinx+Qc39V
1lliBzcTSKrmctK+8/cVFYx2KxtmU50iGluWZKsoWjxeIPqwl6An3MmWM9ZmO8+f
0xKmAAD6AqFvKxN8PlBEzGiaM6PzfNhrbsLuy9YU1XaSwPZrt2ER14hJBBgRAgAJ
BQJOQJqUAhsMAAoJELhfYpnlV0GZ8mgAn3avBPPP79eDQfj6vFgu8LNVCsp3AJsE
O56cXBbZ/vcdyhNuRyghUF0StQ==
=n3z5
-----END PGP PRIVATE KEY BLOCK-----"""
