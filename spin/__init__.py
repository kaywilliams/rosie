"""
spin

A modular, extensible program framework for building customized anaconda-based
Linux distributions.

Highly optimized execution engine attempts to minimize build times by tracking
data on various parts of the build process and only executing stages that have
had input change or that are missing output files.  The goal is to minimize the
time spent repeating unnecessay steps in the build process while still ensuring
that the output is consistenly valid and up-to-date with the available input.

Modular-style system allows easy customization of the build process.  It is
simple to enable or disable entire modules by adding or removing them from a
modules/ directory, or by making an entry in the configuration file.  It is
also easy to extend the basic spin system by writing your own modules that
implement the spin module interface.  

Support for multiple platform builds - spin is capable of building a
distribution based on any version of anaconda from 10.x onward depending on
the software installed on the build machine.  Through the use of multiple
configuration files, one machine can build a variety of custom distributions
based on many different base distributions with no difficulty.  Careful use
of a cache management system ensures that build data files don't take up too
much space on the machine's drive while attempting to minimize cache misses
that eat up valuable time.

See main.py for information on more specific implementation details.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '3.0'
__date__    = 'March 8th, 2007'
