#
# Copyright (c) 2012
# Deploy Foundation. All rights reserved.
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
listcompare.py

A simple list comparison utility.

Iteratively compares two lists, returning elements unique to each list and the
ones in common.
"""

__author__  = "Daniel Musgrave <dmusgrave@deployproject.org>"
__version__ = "1.0"
__date__    = "17 November 2006"

def compare(l1, l2):
  """
  left, right, both = compare(l1, l2)

  Iteratively compare list1 to list2 and list2 to list1, returning a tuple of
  elements unique to list1, elements unique to list2, and common elements,
  respectively
  """

  left = []
  right = []
  common = []

  if isinstance(l1, str): l1 = l1.split()
  if isinstance(l2, str): l2 = l2.split()

  # copy, this operation is destructive
  list1 = l1[:]
  list2 = l2[:]

  list1.sort()
  list2.sort()

  for elem in list1:
    if elem in list2:
      common.append(elem)
      list2.remove(elem)
    else:
      left.append(elem)

  for elem in list2:
    if elem in list1:
      common.append(elem)
      list1.remove(elem)
    else:
      right.append(elem)

  return left, right, common
