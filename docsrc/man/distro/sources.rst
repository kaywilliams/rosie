<source> (top level)
--------------------


The source element of the config file contains configuration related to including
source RPMs (SRPMs) in your custom distribution.


::

	element source {
	  attribute enabled { text },
	  element repo { ... }+
	}


Attributes
**********

source elements have the following attributes:

enabled
+++++++

optional; boolean value indicating whether this event is active or not;
defaults to 'true'



If enabled, spin will include the necessary SRPMs to correspond to the
list of RPMs in the distribution; if it is disabled, any SRPMs will be removed
from existing output.


Parents
*******

distro

Examples
********


The following is an example source element.  Note that the definition includes
a macro element; see the appropriate section for information on how these are
processed.


::

	<sources enabled='true'>
	  <macro id='root'>http://redhat.download.fedoraproject.org<macro>
	  <repo id='fedora-base-src'>
	    <baseurl>%{root}/pub/fedora/linux/core/6/source/SRPMS</baseurl>
	  </repo>
	  <repo id='fedora-extras-src'>
	    <baseurl>%{root}/pub/fedora/linux/extras/6/SRPMS</baseurl>
	  </repo>
	</sources>


