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
resolve.py

Simple dependency resolver

resolve.py provides a Resolver class capable of resolving simple RPM-style
dependencies.  It accepts a list of Item objects and computes an ordering
based on each Item's list of requirements and provisions.  If the list of
Items it is passed is unresolvable, it raises an UnresolvableError.

There are currently three types of relationships between Items that can
affect the final ordering.  Relationships occur between a Producer and a
Consumer.  Producers provide one or more unique strings identifying
something that they provide to other Items.  Consumers are ordered with
relation to the producers according to the relationships they have with
them:

 requires
    a requires relationship indicates that the given Consumer must occur
    after all Producers that provide the given requirement
 comes-before
    a comes-before relationship means that the Consumer must come before
    all instances of Producers that provide the given requirement
 comes-after
    a comes-after relationship means that the Consumer must come after all
    instances of Producers that provide the given requirement

All three above relationships also support a prefix 'conditionally-'; for
example, 'conditionally-comes-before'.  This prefix modifies the behavior
of the relationship slightly; essentially, the listed requirements are
optional; if they exists some Producer that provides the requirement, the
normal relationship is observed; if no such Producer exists, the requirement
is ignored.

As mentioned, this is a somewhat simplistic dependency resolver.  It is not
capable of resolving dependency loops (A->B->C->A), although it can detect
and find them, nor does it support some of the more advanced features of RPM
such as obsoleting and versioning.  (resolve.py is not intended to be used
as an RPM dependency solver; rather, it is intended to provide RPM-like
dependency resolution for other tasks that requires similar functionality.)
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '3.1'
__date__    = 'September 7th, 2007'

from solutionstudio.util import graph

class Item(object):
  "A simple resolution struct that allows dependency solving."
  def __init__(self, id, enabled = True,
                     provides = None,
                     requires = None,
                     comes_before = None,
                     comes_after  = None,
                     conditionally_requires     = None,
                     conditionally_comes_before = None,
                     conditionally_comes_after  = None):
    self.id = id

    self.provides     = set(provides or [])
    self.requires     = set(requires or [])

    self.comes_before = set(comes_before or [])
    self.comes_after  = set(comes_after  or [])

    self.conditionally_requires     = set(conditionally_requires     or [])
    self.conditionally_comes_before = set(conditionally_comes_before or [])
    self.conditionally_comes_after  = set(conditionally_comes_after  or [])

    self.enabled = enabled

  def get_children(self): return []

class Resolver(graph.DirectedGraph):
  """
  Graph-based dependency resolver

  Performs dependency solving using directed graphs (DGs).  Each Event
  is represented as a node in the graph, and each dependency as an edge.
  After all events and dependencies are added, they are ordered using
  the resolve() function.

  Resolver supports the concept of 'tiered dependencies'; specifically,
  that any Event can have one or more children.  Child events inherit
  all the provides of the parent, meaning that they can list in their
  'provides' field provisions that are not actually present within their
  current scope.  Similarly, parent events inherit all the provides and
  requires of their children, meaning that siblings to an Event can
  require something that only the Event's children provide.
  """
  def __init__(self, provs=None, relatives=None):
    """provs is a list of provides that can be implicitly assumed at this
    level (used in provdies-requires relationships); relatives is a list
    of node ids available in the tree (used in conditional-comes-before/
    after relationships)"""
    graph.DirectedGraph.__init__(self)

    self.mapping = {} # map of event ids to EventNodes
    self.provs = provs or []
    self.relatives = relatives or []
    self.Q = [] # queue of nodes to be processed
    self.P = {} # mapping of provide strings to node ids

    self.debug = False # enable to get more verbose output

  def dprint(self, msg):
    if self.debug: print msg

  def add_node(self, item):
    self.dprint('adding item %s' % item)
    if self.mapping.has_key(item.id): return # we've already added this item

    graph.DirectedGraph.add_node(self, item)
    self._add_mapping(item, item)

  def _add_mapping(self, item, maptarget):
    # add a mapping for all child nodes to the highest ancestor; for resolving
    # purposes
    if self.mapping.has_key(item.id): return # we've already added this item

    self.mapping[item.id] = maptarget
    for e in item.get_children():
      self._add_mapping(e, maptarget)

  def resolve(self):
    """
    Attempt to resolve an event ordering based on the current resolve set.  If
    such an ordering cannot be found, raises an UnresolvableError with details
    as to exactly which requirements could not be met.
    """
    unresolved, resolved = self._resolve()

    if len(unresolved) > 0:
      raise UnresolvableError(unresolved)
    else:
      return resolved

  def _resolve(self):
    """
    unresolved, resolved = Resolver._resolve()

    Recursive event resolution function.

    Constructs the queue and provides dictionary used by
    Resolver._construct_dag() to create the event dependency graph.  After
    the graph is complete, uses topological_sort() to attempt to find a
    working event ordering.

    Returns a list of unresolved 'requires' and a sorted list of events.  If
    len(unresolved) == 0, then the event set is said to be 'closed' at the
    current tier; if not, then the parent is expected to provide these
    'requires'.
    """
    unresolved = [] # list of things we can't resolve

    self._preprocess_nodes()  # create a list of provides
    self._process_nodes()     # add all requirementes to queue
    self._postprocess_nodes() # resolve children

    # resolve ordering
    unresolved.extend(self._construct_dag())

    sorted = self.topological_sort()

    return unresolved, sorted

  def _preprocess_nodes(self):
    for node in self.nodes:
      self.dprint('preprocessing node \'%s\'' % node.id)

      # add all provides
      for prov in node.provides:
        self.dprint(' + adding provides: %s' % prov)
        self.P.setdefault(prov, set()).add(node)

  def _process_nodes(self):
    provides = self.P.keys() + self.provs
    relatives = self.mapping.keys() + self.relatives

    # add all requires
    for node in self.nodes:
      self.dprint('processing event %s' % node.id)
      # add all requires
      for req in node.requires:
        self.dprint(' + adding requires: %s' % req)
        self.Q.append(Requires((node.id, req)))

      # add conditionally-requires
      for req in node.conditionally_requires:
        if req in provides:
          self.dprint(' + adding conditionally-requires: %s' % req)
          self.Q.append(Requires((node.id, req)))
        else:
          self.dprint(' + skipping conditionally-requires: %s' % req)

      # add comes-before
      for req in node.comes_before:
        self.dprint(' + adding comes-before: %s' % req)
        self.Q.append(ComesBefore((node.id, req)))

      # add conditionally-comes-before
      for req in node.conditionally_comes_before:
        if req in relatives:
          self.dprint(' + adding conditionally-comes-before: %s' % req)
          self.Q.append(ComesBefore((node.id, req)))
        else:
          self.dprint(' + skipping conditionally-comes-before: %s' % req)

      # add comes-after
      for req in node.comes_after:
        self.dprint(' + adding comes-after: %s'  % req)
        self.Q.append(ComesAfter((node.id, req)))

      # add conditionally-comes-after
      for req in node.conditionally_comes_after:
        if req in relatives:
          self.dprint(' + adding conditionally-comes-after: %s' % req)
          self.Q.append(ComesAfter((node.id, req)))
        else:
          self.dprint(' + skipping conditionally-comes-after: %s' % req)

  def _postprocess_nodes(self):
    # resolve all children nodes
    for n in self.nodes:
      self.dprint('postprocessing node \'%s\'' % n.id)

      if len(n.get_children()) > 0:
        resolver = Resolver(provs=self.P.keys(), relatives=self.mapping.keys())
        for e in n.get_children():
          resolver.add_node(e)
        newreqs, childorder = resolver._resolve()

        n.stitch(childorder) # reorder children according to sort result

        # add all requirements of all children
        for Req in newreqs:
          newreq = Req.__class__((n.id, Req[1]))
          newreq.orignode = Req.orignode # keep track of where this req originated
          if newreq not in self.Q:
            self.dprint(' + adding requirement from child: %s' % newreq[1])
            self.Q.append(newreq)

        # add all provides of all children
        for child in n.get_children():
          for prov in child.provides:
            self.P.setdefault(prov, set())
            if n not in self.P[prov] or n not in n.provides:
              self.dprint(' + adding provide from child: %s' % prov)
            self.P[prov].add(n)
            n.provides.add(prov)

  def _construct_dag(self):
    """
    Construct a directed acyclic graph (DAG) from the nodes already in
    Resolver.G and the 'requires' in Q.  Edges are added between the
    provider and the requiree as they are encountered, until the entire
    graph is populated.  Returns a list of requirements that could not be
    directly handled at this level.
    """
    # resolve ordering
    unresolved = [i for i in self.Q]
    feventid, freq = None, None

    # Q is a queue (what a pun!) of unresolved (event, requirement) pairs
    while len(self.Q) > 0:
      Req = self.Q.pop(0)
      # if we've made a complete cycle without adding any new items, then
      # resolution is impossible
      if (feventid, freq) == Req: break

      found = False

      if   isinstance(Req, Requires):    pfn = self._process_requires
      elif isinstance(Req, ComesAfter):  pfn = self._process_comes_after
      elif isinstance(Req, ComesBefore): pfn = self._process_comes_before
      else: raise TypeError(Req)

      if pfn(Req, unresolved):
        feventid = None; freq = None
        unresolved.remove(Req)
      else:
        self.Q.append(Req)
        self.dprint('   - no matches')
        if feventid is None and freq is None:
          feventid, freq = Req

    return unresolved

  def _process_requires(self, Req, unresolved):
    self.dprint(' @ checking \'%s\' requires \'%s\'' % Req)

    eventid, req = Req

    if req in self.P.keys():
      for source in self.P[req]:
        if source.id == eventid: continue
        self.dprint('   + provided by \'%s\'' % source.id)
        self.add_edge(self.mapping[source.id], self.mapping[eventid])
      return True

    return False

  def _process_comes_after(self, Req, unresolved):
    self.dprint(' @ checking \'%s\' comes-after \'%s\'' % Req)

    eventid, req = Req

    if req in self.mapping.keys():
      self.dprint('   + provided by \'%s\'' % self.mapping[req])
      self.add_edge(self.mapping[req], self.mapping[eventid])
      return True

    return False

  def _process_comes_before(self, Req, unresolved):
    self.dprint(' @ checking \'%s\' comes-before \'%s\'' % Req)

    eventid, req = Req

    if req in self.mapping.keys():
      self.dprint('   + provided by \'%s\'' % self.mapping[req])
      self.add_edge(self.mapping[eventid], self.mapping[req])
      return True

    return False


class BaseRelationship(tuple):
  "Simple struct for a requirement - tracks the original location the require "
  "came from for better error messages"
  def __init__(self, iterable):
    tuple.__init__(self, iterable)
    self.orignode = self[0]

class Requires(BaseRelationship): pass
class ComesBefore(BaseRelationship): pass
class ComesAfter(BaseRelationship): pass

class UnresolvableError(StandardError):
  def __str__(self):
    s = 'Unable to resolve all dependencies:\n'
    for Req in self.args[0]:
      if   isinstance(Req, Requires):    r = 'requires unprovided'
      elif isinstance(Req, ComesBefore): r = 'comes-before nonexistant'
      elif isinstance(Req, ComesAfter):  r = 'comes-after nonexistant'
      s += ' - \'%s\' %s \'%s\'\n' % (Req.orignode, r, Req[1])
    return s
