<iso> (top level)
-----------------


iso is the container for the iso module's configuration data


::

	element iso {
	  attribute enabled { ... },
	  element pkgorder { ... }?
	  & element set { ... }*
	}


Parent
******

distro

Attributes
**********

iso elements have the following attributes:

enabled
+++++++

optional; boolean value controlling whether this event is enabled; defaults
to 'true'



If enabled is true or unspecified, iso sets as defined in the sets list will
be output to the iso directory; if enabled is false, isos will not be generated
and any existing output will be deleted.


Examples
********


The following iso element creates two sets of ISO images from the output
of spin - one at 640 megabytes in size, the second at 700 megabytes.


::

	<iso>
	  <set>CD</set>
	  <set>700M</set>
	</iso>


See also
********

set

<pkgorder>
----------


optional; provides a path to a package order file. The file must be
in the format produced by the Anaconda pkgorder script and consumable by the
Anaconda splittree script; if not provided, spin creates a package order
file using standard values.


::

	element pkgorder { text }


Parents
*******

iso

Examples
********


The following element creates a set of CD images using a file named
"pkgorder" to order the files in the images.  The "pkgorder" file is located
in a folder relative to the distribution configuration (distro.conf) file.


::

	<iso>
	  <pkgorder>pkgorder</pkgorder>
	  <set>cd</set>
	</iso>


See also
********

path

<set>
-----


set elements are used by spin to determine the size of an iso set to
generate.  The output trees are automatically split so that each iso is smaller
than the specified size.  Sizes are indicated by a number in bytes, a number
followed by an ordinal ('K', 'M', 'G', etc., optionally followed by a 'B'),
or one of the reserved values 'CD' and 'DVD' (which map to '640MB' and '4.7GB',
respectively).  Size indicators and reserved values are case-insensitive.



If the size of a set changes to an equivalent size with a different name between
executions of spin, the output folder's name is changed without recreating
the ISO images in order to save time.


::

	element set { text }


Restrictions
************

The size given for the set must be larger than 100 MiB.

Parents
*******

iso

Examples
********

See iso for an example of a set element

