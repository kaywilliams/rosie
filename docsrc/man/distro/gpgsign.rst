<public-key>
------------


Element describing to gpgsign where to find an exported RPM GPG public key that
can be used to sign RPMs.


::

	element public-key { text }


Parents
*******

gpgsign

See also
********

secret-key, passphrase

<secret-key>
------------


Element describing to gpgsign where to find an exported RPM GPG secret key that
can be used to sign RPMs.


::

	element secret-key { text }


Parents
*******

gpgsign

See also
********

public-key, password

<passphrase>
------------


Optional element for use by gpgsign in providing a passphrase to gpg when signing
RPMs.  If this element is not present, spin will prompt the user for the
passphrase before continuing.  Note - use of this element is discouraged in most
cases, as it stores your gpg passphrase in plaintext mode.


::

	element passphrase { text }


Parents
*******

gpgsign

<gpgsign> (top level)
---------------------


gpgsign is the container for the gpgsign module's configuration data.


::

	element gpgsign {
	  attribute enabled { ... }
	  & (
	    element public-key { ... }
	    & element secret-key { ... }
	    & element passphrase { ... }?
	  )?
	}


Parents
*******

distro

Attributes
**********

gpgsign elements have the following attributes:

enabled
+++++++

optional; boolean value indicating whether this event is active or not;
defaults to 'true'



If enabled, all RPMs included in the distribution are signed with the
gpg keys specified in the public and secret elements; if it is disabled,
gpgkeys will be removed from any existing output.


Examples
********


The following gpgsign element will cause spin to sign each RPM that is
included in the custom distribution it generates by utilizing the GPG keys
that are specified in the public and secret elements.


::

	<gpgsign enabled='true'>
	  <public-key>/var/gpg/gpg-public-key-export</public-key>
	  <secret-key>/var/gpg/gpg-secret-key-export</secret-key>
	</gpgsign>


