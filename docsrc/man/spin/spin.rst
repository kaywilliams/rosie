=========
spin.conf
=========

---------------------------
configuration file for spin
---------------------------

:Manual section: 5

SYNOPSIS
========

spin.conf synopsis

CONFIG ELEMENTS
===============
Detailed below is a comprehensive list of XML elements available in the spin config file.

<disable-module>
----------------


allows a specific module to be globally disabled. The text value of the 
element is the name of a spin module located in a lib-path. If a module is 
disabled, it will never be loaded by Spin, even if it is specified in the 
distribution configuration file (distro.conf). For example, if 'iso' is 
listed as a disabled module, it will not be loaded, even if the distro.conf 
contains an iso element such as the following, 
'<iso><set>dvd</dvd></iso>'


::

	element spin {
	  element disable-module { ... }+
	}


Parents
*******

spin

Examples
********


In the following example, the 'gpgcheck' and 'iso' modules are disabled.


::

	<disable-module>gpgcheck</disable-module>
	<disable-module>iso</disable-module>


