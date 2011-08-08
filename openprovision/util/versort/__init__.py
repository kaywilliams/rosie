"""
versort.py

Sorting library for version strings

Simplified version of the original sortlib.py

Delimiters

Delims, or 'delimiters', are the characters that separate the various
fields used for comparison.  The default set of delimiters is ['-', '.'],
which is the standard set of delimiters used in NVR-style version numbers
(like those that RPM uses).  All standard API functions accept a delim
argument which allows you to specify differet sets of delimiters.  You are
not limited to two levels; you can use as few or as many as you want.

The order of delimiters is significant.  The leftmost delimiter indicates
the greatest amount of separation between its neighbors while the rightmost
signifies the least.  For example, in the RPM name 'example-1.0-25', the
'-' characters separate the name ('example'), version ('1.0'), and release
('25') fields, while the '.' character separates the major ('1') and minor
('0') version numbers.
"""

__author__  = "Daniel Musgrave <dmusgrave@openprovision.com>"
__version__ = "2.0"
__date__    = "April 3rd, 2008"

from util import *

DELIMS_DEFAULT = ['-','.'] # handles NVR-style versions

# API FUNCTIONS
def sort(l, delims=None):
  "Sort a list of items that need to be deformatted first before being sorted"
  return _sort(deformat_list(l,delims))

def highest(l, delims=None):
  "Get the highest item from a list that needs to be deformatted"
  return _highest(deformat_list(l,delims))

def lowest(l, delims=None):
  "Get the lowest item from a list that needs to be deformatted"
  return _lowest(deformat_list(l,delims))

def deformat(s, delims=None):
  "Create a (possibly nested) TokenGroup from a string"
  if delims is None: delims = DELIMS_DEFAULT
  return _deformat(s, delims=delims)

def deformat_list(l, delims=None):
  "Deformat a list of strings"
  return [ deformat(x, delims) for x in l ]

Version = deformat # factory function alias

# testing
T = ['5','4','3','2','1','10','2alpha','2beta','2.1','3-4.1','3-4','3-4-5']
