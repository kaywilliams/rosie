#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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
imerge.py

Incrementally merges XML documents using the merge API.  Expects a document
containing one or more 'entry containers', each of which defines a certain XML
tree to be modified.  These trees are standard merge trees that contain at a
minimum a version attribute, which indicates the version to which the child
nodes pertain.  The incremental_merge() function is passed this tree as well as
an index, which determines how many of the merge trees to apply to the
primary tree (the tree with the lowest index).  All merge trees with the version
attribute less than or equal to the passed index get merged, in order, onto the
primary tree.  The final result is returned.

See merge for details on the merge API and its behavior.
"""

__author__  = "Daniel Musgrave <dmusgrave@renditionsoftware.com>"
__date__    = "February 15th, 2007"
__version__ = "1.0"

import copy

from solutionstudio.util import versort

from solutionstudio.util.rxml import merge

def incremental_merge(entries, index):
  indexes = entries.xpath('*/@version')
  indexes = versort.sort(indexes)
  base    = indexes.pop(0)

  tree = copy.deepcopy(entries.get('*[@version="%s"]' % base))

  # make sure all trees set the allowoverride attribute
  tree.getroot().attrib['allowoverride'] = 'True'
  # set up the correct version attribute
  tree.getroot().attrib['version'] = index

  handler = merge.XmlMergeHandler(tree)

  for i in indexes:
    if i <= index:
      entry = entries.get('*[@version="%s"]' % i)
      mergetree = copy.deepcopy(entry)
      handler.merge(mergetree)
    else:
      break # indexes are sorted, so once the index is greater, we're done merging

  return handler.root
