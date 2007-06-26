""" 
resolve.py

Simple dependency resolver

resolve.py provides a Resolver class capable of resolving simple RPM-style
dependencies.  It accepts a list of event.Event objects and computes an
ordering based on each Event's 'provides', 'requires', and 'conditional-
requires' fields.  If the list of Events it is passed is unresolvable, it
raises an UnresolvableError.

A 'provide' is a string representing something that a given Event creates,
changes, or otherwise can provide to other events.  A 'require' corresponds
directly with a provide; it represents a file, object in memory, or other
requirement that an Event has before it can run.  A 'require' is satisfied
if another Event has a 'provide' with the same contents that occurs earlier
in the execution sequence.  A 'conditional-require' is exactly the same as
a 'require' except that if no Event has a 'provide' with the same name, no
error is raised.

As mentioned, this is a somewhat simplistic dependency resolver.  It is not
capable of resolving dependency loops (A->B->C->A), although it can detect
and find them, nor does it support soem of the more advanced features of RPM
such as obsoleting and versioning.  (resolve.py is not intended to be used
as an RPM dependency solver; rather, it is intended to provide RPM-like
dependency resolution for other tasks that requires similar functionality.)
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 8th, 2007'

from dims import graph

class Item:
  "A simple resolution struct that allows dependency solving."
  def __init__(self, provides=[], requires=[], conditional_requires=[],
                     enabled=True):
    self.provides = provides
    self.requires = requires
    self.conditional_requires = conditional_requires
    self.enabled = enabled

class EventNode(graph.DirectedNode):
  """ 
  A subclass of graph.DirectedNode that keeps track of children nodes as well as
  siblings.  Also defines an iterator over self and children.
  """
  def __init__(self, data):
    graph.DirectedNode.__init__(self, data)
    
    self.children = []
  
  def __iter__(self):
    yield self
    for child in self.children:
      for c in child:
        yield c
      if len(child.children) > 0:
        yield -1

class ResolveResult:
  """Simple class representing the outcome of running Resolver.resolve(), below.
  Contains an iterator which will yield the contents of the resolved set without
  yielding itself."""
  def __init__(self, result):
    self.result = result
  
  def __iter__(self):
    for result in self.result:
      for n in result:
        yield n
      if len(result.children) > 0:
        yield -1

class Resolver:
  """ 
  Graph-based dependency resolver
  
  Performs dependency solving using directed graphs (DGs).  Each Event is represented
  by a EventNode and each dependency by a graph.DirectedEdge.  After all Events and
  dependencies are added, they can be ordered by using the resolve() function.
  
  Resolver supports the concept of tiered dependencies; specifically, that any Event
  can have one or more children.  Child events inherit all the provides of the parent,
  meaning that they can list in their 'provides' field provisions that are not actually
  present within their current scope.  Similarly, parent events inherit all the
  provides of their children, meaning that siblings to an Event can require something
  that only the Event's children provide.
  """
  def __init__(self):
    self.G = graph.DirectedGraph()
    
    self.mapping = {} # map of event ids to EventNodes
    
    self.debug = False # enable to get more verbose output
  
  def dprint(self, msg):
    if self.debug: print msg
    
  def create_event_nodes(self, events):
    "Add a list of events, and all their children, to the resolve set"
    for event in events:
      self.dprint('adding event %s' % event)
      if self.mapping.has_key(event.id): continue # we've already added this event
      
      node = EventNode(event)
      self.G.add_node(node)
      self.mapping[event.id] = node
  
  def resolve(self):
    """ 
    Attempt to resolve an event ordering based on the current resolve set.  If
    such an ordering cannot be found, raises an UnresolvableError with details
    as to exactly which requirements could not be met.
    """
    unresolved, resolved = self._resolve()
    
    if len(unresolved) > 0:
      raise UnresolvableError, unresolved
    else:
      return ResolveResult(resolved)
  
  def _resolve(self, provs=[]):
    """ 
    unresolved, resolved = Resolver._resolve(provs=[])
    
    Recursive event resolution function.  Accepts a single parameter, provs, a list
    of the 'provides' we can assume the parent provides to us at the given level.
    
    Constructs the queue and provides dictionary used by Resolver._construct_dag()
    to create the event dependency graph.  After the graph is complete, uses
    topological_sort() to attempt to find a working event ordering.
    
    Returns a list of unresolved 'requires' and a sorted list of events.  If
    len(unresolved) == 0, then the event set is said to be 'closed' at the current
    tier; if not, then the parent is expected to provide these 'requires'.
    """
    unresolved = [] # list of things we can't resolve
    # add node requirements to a queue, store provides in a list
    Q = []
    P = {}
    
    # process all events
    for node in self.G.nodes:
      self.dprint('preprocessing event %s' % node.data.id)
      
      # add all requires
      for req in node.data.requires:
        self.dprint(' + adding requirement: %s' % req)
        Q.append((node.data, req))
      
      # add all provides
      for prov in node.data.provides:
        if not P.has_key(prov): P[prov] = []
        self.dprint(' + adding provide: %s' % prov)
        P[prov].append(node.data)
    
    # add conditional requirements
    for node in self.G.nodes:
      self.dprint('preprocessing event %s' % node.data.id)
      for req in node.data.conditional_requires:
        if req in P.keys():
          self.dprint(' + adding conditional-requirement: %s' % req)
          Q.append((node.data, req))
    
    # resolve all children nodes
    for n in self.G.nodes:
      if len(n.data.get_children()) > 0:
        resolver = Resolver()
        resolver.create_event_nodes(n.data.get_children())
        newreqs, childorder = resolver._resolve(provs=provs + P.keys())
        
        n.children = childorder
        
        self.dprint('postprocessing event %s' % n.data.id)
        # add all requirements of all children
        for req in newreqs:
          self.dprint(' + adding requirement: %s' % req)
          Q.append((n.data, req))
          unreq = self._construct_dag(Q, P, provs)
          if len(unreq) > 0:
            raise UnresolvableError, [ (n.data, req) for req in unreq ]
        
        # add all provides of all children
        for child in n.data.get_children():
          for prov in child.provides:
            if not P.has_key(prov): P[prov] = []
            self.dprint(' + adding provide: %s' % prov)
            P[prov].append(n.data)
    
    # resolve ordering
    unresolved.extend(self._construct_dag(Q, P, provs))
    
    sorted = self.G.topological_sort()
    
    return unresolved, sorted

  def _construct_dag(self, Q, P, provs=[]):
    """ 
    Construct a directed acyclic graph (DAG) from the nodes already in Resolver.G
    and the 'requires' in Q.  Edges are added between the provider and the requiree
    as they are encountered, until the entire graph is populated.  Returns a list
    of requirements that could not be directly handled at this level.
    """
    # resolve ordering
    unresolved = []
    fevent, freq = None, None
    
    # Q is a queue (what a pun!) of unresolved (event, requirement) pairs
    while len(Q) > 0:
      event, req = Q.pop(0)
      found = False
      
      self.dprint(' @ checking %s requires %s' % (event.id, req))
      
      # if we've made a complete cycle without adding any new items, then resolution
      # is impossible
      if fevent == event and freq == req:
        raise UnresolvableError, Q + [(event, req)]
      
      # P is a dictionary of provide keys to events that provide them
      # check this dictionary to see if some event provides this item
      if req in P.keys():
        for source in P[req]:
          if source.id == event.id: continue
          self.dprint('   + provided by %s' % source.id)
          self.G.add_edge(self.mapping[source.id], self.mapping[event.id])
        fevent, freq = None, None
        found = True
      # provs is a list of provides given by the event's parent
      if req in provs:
        self.dprint('   + provided by parent %s' % event.parent.id)
        unresolved.append(req)
        fevent, freq = None, None
        found = True
      
      # if no matches were found, put the requirement back on the queue and continue
      if not found:
        Q.append((event, req))
        self.dprint('   - no matches')
        if fevent is None and freq is None:
          fevent, freq = event, req
    
    return unresolved
  

class UnresolvableError(StandardError):
  def __str__(self):
    str = 'Unable to resolve all dependencies:\n'
    for deptup in self.args[0]:
      str += ' - \'%s\' requires unprovided \'%s\'\n' % deptup
    return str
