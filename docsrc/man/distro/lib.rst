<baseurl>
---------

The baseurl element is used inside of repo elements and accepts the
same values as path elements.

::

	element baseurl {  text  }


Parents
*******

repo

See also
********

path, repo, repos, sources

<exclude-package>
-----------------


exclude-package indicates a package that should be explicitly excluded
from some operation, even if it would normally be included in some other
way.  For example, the comps element uses exclude-package to list
packages that shouldn't be included in the required packages list, even
if they are included in one of the groups it contains.


::

	element exclude-package { text }


Parents
*******

comps, repos, repo

See also
********

comps, repos, repo

<include-package>
-----------------


include-package indicates packages that should be included from a
repository.  For example, if only one package is specified via an
include-package, then that is the *only* package spin will see from the
repository when dependency solving.


::

	element include-package { text }


Parents
*******

repo

See also
********

exclude-package

<path>
------


A valid URI utilizing one of the following supported protocols: file, http,
and https.  If no protocol is specified, 'file' is typically assumed.  If the
path is relative instead of absolute, spin assumes a relative file path
to ...somewhere...


::

	element path {
	  attribute dest { text }?,
	  attribute mode { text }?,
	  attribute filename { text }?,
	  text
	}


Attributes
**********

path elements have the following attributes:

dest
++++

optional; some path elements are used as both a source and a destination;
for these cases, the dest attribute tells spin where to put the file
or directory; events that do not use dest ignore it; defaults to '/'



Any path specified (including the default) will have all leading '/'
characters stripped to ensure proper joining - to treat the destination
specified as an absolute path, join it with the string '/'.


mode
++++

optional; controls the mode of the file in the destination; defaults
to '644'

filename
++++++++

optional; sets the filename (basename) of the file in the destination;
defaults to the basename of the source file.


Parents
*******

isolinux, product.img, repo, updates.img, use-existing

Examples
********


The following are a few examples of path elements


::

	<path>http://redhat.download.fedoraproject.org/pub/</path>



This is a simple web location, pointing to the 'pub' folder at the given
server.


::

	<path>/var/cache/profiles</path>
	<path>file:///var/cache/profiles</path>



These are equivalent paths to a file location on the local machine.  It is
uncertain whether this is a file or a directory; in most cases is is
recommended that trailing directories are affixed with a '/' to be clear.


::

	<path>source/schema/di.xml</path>



This is an example relative path.  This path is appended onto the relative
path root ...defined somehow...


::

	<path dest='/var/cache'>/var/cache/profiles</path>



This is a path that includes a dest attribute.  If spin copies this file
somewhere, it will have 'var/cache' appended to the destination before copying.


<repo>
------


repo elements represent a local or remote repository that can be used by
spin as a source for input files, including rpms, stage2 images, kernels
and initrds, and other files.  They contain a number of nodes that define all
the characteristics of a repository for spin's use.


::

	element repo {
	  attribute id { text },
	  element baseurl { ... }
	  & element include-package { ... }*
	  & element exclude-package { ... }*
	  & element gpgkey { ... }?
	  & element gpgcheck { ... }?
	  & element include-package { ... }?
	}


Parents
*******

repos, sources

Attributes
**********

repo elements have the following attributes:

id
++
a unique id representing this repo in the config file

Examples
********


The following is an example repository element.  Note that the definition
includes a macro element; see the appropriate section for information on
how these are processed.


::

	<repo id='example-fedora-repo'>
	  <macro id='root'>http://redhat.download.fedoraproject.org<macro>
	  <baseurl>%{root}/pub/fedora/linux/core/6/i386/os/</baseurl>
	  <gpgkey>
	    %{root}/pub/fedora/linux/core/6/i386/os/RPM-GPG-KEY-fedora
	  </gpgkey>
	  <gpgcheck>yes</gpgcheck>
	</repo>


