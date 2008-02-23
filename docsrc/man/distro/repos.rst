<base-repo>
-----------

Todo - Add description and example.


::

	element base-repo {
	  text
	}


Parents
*******

repos

<exclude-package>
-----------------

optional; used to identify a package to exclude both when generating
the comps file and when resolving dependencies to generate the package
list. Takes the name of an RPM as the text value.

::

	element exclude-package {
	  text
	} *


Parents
*******

repos

<gpgkey>
--------

optional; Some RPMs are signed with a gpgkey, allowing end users to
validate their contents.  The gpgkey element points to an exported RPM
GPG public key that can be used to validate a repository's RPMs.


::

	element gpgkey {
	  attribute check { text },
	  text
	}


Attributes
**********

gpgkey elements have the following attributes:

check
+++++

optional; boolean value indicating whether or not to actually check the
RPMs against this key; defaults to 'false'


Parents
*******

repo

<repos> (top level)
-------------------


The repos element contains configuration data regarding the source repositories
from which to gather RPMs for the custom distribution.  It lists each
repository separately, along with any and all information required to download
files from it.



The repos container must contain one base-repo element and one or more repo 
elements.  The base-repo element contains the id of the reposistory to be used 
as the source for several other important distribution files, including group files, 
stage 2 images, and isolinux files.  


::

	element repos {
	  element base-repo { example-repo }
	  element exclude-package { package-name }*
	  element repo { attribute id { 'example-repo' } ... }*
	}


Parents
*******

distro

Examples
********


A repos element consists of multiple repo elements; see repo for an example
of repo elements.


