#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
"""
solutionstudio

A modular, extensible program framework for building customized anaconda-based
Linux solutions.

Highly optimized execution engine attempts to minimize build times by tracking
data on various parts of the build process and only executing stages that have
had input change or that are missing output files.  The goal is to minimize the
time spent repeating unnecessay steps in the build process while still ensuring
that the output is consistenly valid and up-to-date with the available input.

Modular-style system allows easy customization of the build process.  It is
simple to enable or disable entire modules by adding or removing them from a
modules/ directory, or by making an entry in the configuration file.  It is
also easy to extend the basic solutionstudio system by writing your own modules that
implement the solutionstudio module interface.

Support for multiple platform builds - solutionstudio is capable of building a
solution based on any version of anaconda from 10.x onward depending on
the software installed on the build machine.  Through the use of multiple
configuration files, one machine can build a variety of solutions
based on many different base distributions with no difficulty.  Careful use
of a cache management system ensures that build data files don't take up too
much space on the machine's drive while attempting to minimize cache misses
that eat up valuable time.

See main.py for information on more specific implementation details.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '3.0'
__date__    = 'March 8th, 2007'
