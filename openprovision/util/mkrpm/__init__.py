#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
Python module that can be used to read, write, build and modify RPMs.
"""

__author__ = 'Uday Prakash <uprakash@openprovision.com>'
__date__   = 'September 11, 2007'

from rpmsign  import *
from rpmbuild import *

__all__ = [
  'callback',
  'globals',
  'package',
  'rpmbuild',
  'rpmsign',
]
