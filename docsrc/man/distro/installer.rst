<installer> (top level)
-----------------------


installer is the top level container for configuration related to installation
images and other files.


::

	element installer {
	  element release-files { ... }?
	  & element logos { ... }?
	  & element initrd.img { ... }?
	  & element product.img { ... }?
	  & element updates.img { ... }?
	  & element isolinux { ... }?
	}


Parents
*******

distro

