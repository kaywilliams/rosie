#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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
tree.py

Defines a basic node structure which can be linked together to form node trees.
"""

class NodeMixin:
  """
  A node is a single element within a tree.  It contains pointers to its parent,
  first and last children, and previous and next sibling.  By utilizing these
  pointers, the entire tree can be traversed with relative ease (see depthfirst()
  for an example).

  It is important to note that nodes have no direct concept of the entire set of
  their children, as they only have pointers to their first and last.  Thus, in
  order to access all of a node's children, it is necessary to use the
  get_children() function.
  """
  def __init__(self, parent=None):
    self.nextsibling = None
    self.prevsibling = None
    self.firstchild = None
    self.lastchild = None

    if parent is not None:
      parent.append_child(self)
    else:
      self.parent = None

  def append_child(self, child):
    "Add a child node to the end of this node's children"
    if self.lastchild is not None:
      assert self.firstchild is not None
      self.lastchild.nextsibling = child
      child.prevsibling = self.lastchild
    else:
      assert self.firstchild is None
      child.prevsibling = None
      self.firstchild = child
    child.nextsibling = None
    child.parent = self
    self.lastchild = child

  def prepend_child(self, child):
    "Add a child node to the beginning of this node's children"
    if self.firstchild is not None:
      assert self.lastchild is not None
      self.firstchild.prevsibling = child
      child.nextsibling = self.firstchild
    else:
      assert self.lastchild is None
      child.nextsibling = None
      self.lastchild = child
    child.prevsibling = None
    child.parent = self
    self.firstchild = child

  def append_sibling(self, sibling):
    "Insert a sibling between this node and its next sibling"
    if self.nextsibling is not None:
      self.nextsibling.prevsibling = sibling
    sibling.nextsibling = self.nextsibling
    sibling.parent = self.parent
    sibling.prevsibling = self
    self.nextsibling = sibling

  def prepend_sibling(self, sibling):
    "Insert a sibling between this node and its previous sibling"
    if self.prevsibling is not None:
      self.prevsibling.nextsibling = sibling
    sibling.prevsibling = self.prevsibling
    sibling.parent = self.parent
    sibling.nextsibling = self
    self.prevsibling = sibling

  def get_children(self):
    "Return a list of all children of this node"
    if self.firstchild is None:
      return []
    else:
      curchild = self.firstchild
      children = [curchild]
      while curchild.nextsibling is not None:
        curchild = curchild.nextsibling
        children.append(curchild)
      return children

  def stitch(self, nodes):
    "Stitch together node's children in the order presented in nodes list"
    for node in nodes:
      assert node.parent == self
    return stitch(nodes, self)

  def get_previous(self):
    if self.prevsibling:
      return self.prevsibling.get_last_descendant() or self.prevsibling
    else:
      return self.parent

  def get_next(self):
    return self.get_first_descendant() or self.nextsibling or None

  def get_first_descendant(self):
    return self.firstchild

  def get_last_descendant(self):
    if self.lastchild:
      return self._get_last_descendant()
    else:
      return None

  def _get_last_descendant(self):
    if self.lastchild:
      return self.lastchild._get_last_descendant()
    else:
      return self


def depthfirst(tree):
  "Traverse a node tree in a depth-first manner"
  if tree:
    yield tree
    for x in depthfirst(tree.firstchild):  yield x
    for x in depthfirst(tree.nextsibling): yield x

def stitch(nodes, parent=None):
  "'Stitch' nodes together in the order they appear in list"
  if nodes is None or len(nodes) == 0: return nodes

  for i in range(0, len(nodes)):
    # set prevsibling
    if i == 0:
      nodes[i].prevsibling = None
      if parent is not None: parent.firstchild = nodes[i]
    else:
      nodes[i].prevsibling = nodes[i-1]

    # set nextsibling
    if i == len(nodes)-1:
      nodes[i].nextsibling = None
      if parent is not None: parent.lastchild = nodes[i]
    else:
      nodes[i].nextsibling = nodes[i+1]

    # set parent
    if parent is not None:
      nodes[i].parent = parent

  return nodes
