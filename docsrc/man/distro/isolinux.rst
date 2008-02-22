<initrd.img>
------------


The initrd.img element allows the user to specify one or more files to be
added to the initrd.img used by spin.  Files are added by listing them
in path element; if a destination aside from the root of the image is desired,
this can be accomplished by using the path's 'dest' attribute.


::

	element initrd.img {
	  element path { ... }*
	}


Parents
*******

installer

<isolinux>
----------


The isolinux lement allows the user to specify one or more files to be
included in the isolinux folder created by spin.


::

	element isolinux {
	  element path { ... }*
	}


Parents
*******

installer

