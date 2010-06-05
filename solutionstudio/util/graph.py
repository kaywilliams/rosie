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
graph.py

Somewhat rudimentry implementation of directed graphs in python.  Provides DirectedNode,
DirectedEdge, and DirectedGraph objects.  Also supports topological sorting and cycle
detection.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '0.1'
__date__    = 'June 8th, 2007'

import copy

class DirectedNodeMixin:
  """
  A mixin class that other classes can inherit to allow them to be used in
  graphs.
  """
  def __init__(self):
    self.incoming = set()
    self.outgoing = set()

  in_degree  = property(lambda self: len(self.incoming))
  out_degree = property(lambda self: len(self.outgoing))

  def is_source(self): return self.in_degree  == 0
  def is_sink(self):   return self.out_degree == 0

  def add_edge(self, dest):
    "Add a new edge from this node to dest, returning the new edge"
    return DirectedEdge(self, dest)


class DirectedNode(DirectedNodeMixin, object):
  """
  A directed node that contains a data field for storing primitive types (or
  anything else).
  """
  def __init__(self, data=None):
    DirectedNodeMixin.__init__(self)
    self.data = data

  def __str__(self):
    return str(self.data)

  def __repr__(self):
    ##return '<graph.DirectedNode data=\'%s\'>' % repr(self.data)
    return self.__str__() #!


class DirectedEdge(object):
  """
  Class representing an edge in a directed graph.  Has start and end fields which
  are pointers to the DirectedNode object to which this edge is attached.  Also has
  a weight field representing the weight of this edge (optional).

  Subclasses may define additional fields as desired.
  """
  def __init__(self, start, end, weight=None):
    self.start = start
    self.end   = end
    self.weight = weight

    # automatically add the edge to the start and end nodes
    self.start.outgoing.add(self)
    self.end.incoming.add(self)

  def __eq__(self, other):
    if not isinstance(other, DirectedEdge): return False
    return self.start  == other.start and \
           self.end    == other.end and \
           self.weight == other.weight

  def __str__(self):
    return '%s => %s' % (self.start, self.end)
  def __repr__(self):
    ##return '<graph.DirectedEdge %s => %s>' % (repr(self.start), repr(self.end))
    return self.__str__() #!

  def __hash__(self):
    # allows DirectedEdges to be put into sets
    return hash(self.__str__())

class DirectedGraph(object):
  """
  Class representing a directed graph.  Contains a list of all nodes and edges
  contained in the graph; these can be used in many ways, including sorting, graph
  traversal, closure computation, etc.
  """
  def __init__(self, nodes=[]):
    self.nodes = []
    self.edges = set()

    for node in self.nodes:
      self.add_node(node)

  def __str__(self):
    "Print out a simple string representation of the nodes and edges in the graph"
    ret = ''
    for node in self.nodes:
      if len(node.outgoing) == 0:
        ret += str(node) + '\n'
      else:
        for edge in node.outgoing:
          ret += str(edge) + '\n'
    return ret

  def add_node(self, node):
    "Add node to the graph.  If the node has any edges, add them also"
    self.nodes.append(node)
    for edge in node.incoming.union(node.outgoing):
      self.edges.add(edge)

  def add_edge(self, start, end):
    "Add an edge to the graph starting from node start and ending at node end"
    self.edges.add(DirectedEdge(start, end))

  def topological_sort(self):
    """
    Perform a topological sort on the nodes and edges in the tree.

    Basic algorithm: add all nodes that are sources (no incoming edges) to a queue.
    While the queue is not empty, pop off the first item, output it, and remove all
    its outgoing edges from the graph.  If any of the nodes these edges pointed to
    are now sources, add them to the queue.  Once the queue is empty, if the graph
    has no remaining edges, return; else, the graph has a cycle; find the cycles and
    raise a GraphCycleError.
    """
    G = copy.copy(self) # operations are destructive, so make a copy
    q = [] # queue
    sorted = [] # sorted list (return value)

    # add all source nodes to the queue
    for n in G.nodes:
      if n.is_source():
        q.append(n)

    # traverse the graph, removing edges as they are processed
    while len(q) > 0:
      n = q.pop(0)
      sorted.append(n)
      for e in n.outgoing:
        G.edges.remove(e)
        #e.start.outgoing.remove(e) # this breaks things for some reason
        e.end.incoming.remove(e)
        if e.end.is_source():
          q.append(e.end)

    # if, when done, there are still edges left, we have at least one cycle
    if len(G.edges) > 0:
      print G #!
      raise GraphCycleError(self.find_cycles(G))

    return sorted

  def find_cycles(self, G):
    """
    Method for finding cycles in a graph.  A cycle is a path in a graph
    from which a node can reach itself by following a certain sequence of
    edges.  Returns a list of cycles (represented as lists of edges).

    Basic algorithm - compute a depth-first search from each node in the
    graph, visiting all reachable children.  If any child in the path is
    equal to the starting node, add the cycle to the cycle list.  In order
    to avoid recomputing paths, nodes are added to a processed list once
    they have been fully processed; these nodes are not visited by
    subsequent tree traversals.

    (The previous is the equivalent of removing the nodes from the graph
    entirely.  This may be done at some point in the future.)
    """
    cycles = []
    processed = []
    for n in G.nodes:
      cycles.extend(self._find_cycles(n, n, [], processed))
      processed.append(n)

    return cycles

  def _find_cycles(self, curr, source, stack, processed):
    """
    Recursive cycle finder
     @param curr      : the current node to process
     @param source    : the node at which the cycle starts
     @param stack     : the current stack of edges taken from the start
                        node to the curr node
     @param processed : a list of nodes that have already been completely
                        processed and should be ignored by _find_cycles()
    """
    #self.dprint('_find_cycles(%s, %s, %s, %s)' % (curr, source, stack, processed))
    cycles = []
    for e in curr.outgoing:
      newstack = stack + [e]
      if e.end == source:
        #self.dprint(newstack)
        cycles.append(newstack)
      elif e.end in processed:
        #self.dprint('continue')
        continue
      else:
        cycles.extend(self._find_cycles(e.end, source,
                                        newstack, processed + [curr]))
    return cycles


class GraphCycleError(StandardError):
  def __str__(self):
    str = 'Graph contains one or more cycles:\n'
    i = 1
    for cycle in self.args[0]:
      str += 'cycle %d\n' % i
      for edge in cycle:
        str += '  %s\n' % edge # these are DirectedEdges
      i += 1
    return str
