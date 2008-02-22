<local-webroot>
---------------


The local-webroot element is the directory serving as the build machine's web
root (same as 'DocumentRoot' in httpd.conf, for example).  This, when combined
with the path-prefix element, form the path to the directory into which new
custom builds are published.


::

	element local-webroot { text }


Parent
******

publish

See also
********

path-prefix

<path-prefix>
-------------


The path-prefix element is appended onto the end of local-webroot and
remote-webroot elements to determine the publish directory for local and remote
machines, respectively.  In other ways, it is similar to a standard path
element.


::

	element path-prefix { text }


Parent
******

publish

See also
********

local-webroot, remote-webroot

<publish> (top level)
---------------------


The publish section contains data relevant to 'publishing' the distribution
created by spin to a web-accessible location on the build machine.


::

	element publish {
	  element remote-webroot { ... }?
	  & element local-webroot { ... }?
	  & element path-prefix { ... }?
	  & element repofile { ... }?
	}


Parent
******

distro

Examples
********

The following is an example publish element:

::

	<publish>
	  <remote-webroot>http://www.example.com</remote-webroot>
	  <local-webroot>/var/www/html</local-webroot>
	  <path-prefix>software/custom_distros</path-prefix>
	</publish>



The above config section instructs spin to publish the distribution it
creates to '/var/www/html/software/custom_distros'.  Other computers can then
access the distribution by navigating to 'http://www.example.com/software/custom_distros'


<remote-webroot>
----------------


The remote-webroot element indicates the URL address of the publishing
machine as seen from other computers that will allow them to access
custom distributions published by the build machine. It contains no
directory information; merely the server portion of the url.  When
combined with path-prefix, this forms a full URL to allow remote access to
spin-created distributions.


::

	element remote-webroot { text }


Parent
******

publish

See also
********

path-prefix

Attributes
**********

the remote-webroot element has the following attributes:

use-hostname
************

optional; boolean value indicating whether the hostname (e.g.
        machine1.example.org) should be used in place of the ipaddress
        (e.g. 10.10.0.28) for specifying the web address to the build machine;
        defaults to 'false'.
        

Examples
********


The following are examples of remote-webroot elements.  In these examples,
assume the ipaddress for the build machine is 10.10.0.28 and the hostname
is machine1.example.org.


::

	<remote-webroot use-hostname="false"></remote-webroot>



In this example, the remote webroot would be calculated as
"http://10.10.0.28"


::

	<remote-webroot use-hostname="true"></remote-webroot>



In this example, the remote webroot would be calculated as
"http://machine1.example.org"


::

	<remote-webroot>http://distros.example.org/</remote-webroot>



In this example, the resulting webroot is independent of the machine
used to build the distribution. It is calculated as
"http://distros.example.org"


