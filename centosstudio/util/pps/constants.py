#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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
constants.py

A place to put constants relevant to pps operation
"""

# file types
TYPE_FILE = 0001
TYPE_DIR  = 0010
TYPE_LINK = 0100

# permutations
TYPE_NOT_FILE = TYPE_DIR  | TYPE_LINK
TYPE_NOT_DIR  = TYPE_FILE | TYPE_LINK
TYPE_NOT_LINK = TYPE_FILE | TYPE_DIR

# base class for file paths
import os
_base = str
try:
  if os.path.supports_unicode_filenames:
    _base = unicode
except AttributeError:
  pass
del os
