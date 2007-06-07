""" 
resolve.py

Simple dependency resolver

resolve.py provides a function, resolve(), capable of resolving simple RPM-style
dependencies.  It takes a list of Item objects and computes an ordering based on
each Item's 'provides' and 'requires' fields.  If the list of Items it is passed
is unresolvable, it raises an UnresolvableError.

As mentioned, this is a very simplistic dependency resolver.  It is not capable
of resolving dependency loops (A->B->C->A) nor does it support some of the more
advance features of RPM such as obsoleting and versioning.  (resolve is not
intended to be used as an RPM dependency solver; rather, it is intended to provide
RPM-like dependency resolution for other tasks that require similar functionality.)

Note: this file could be moved into a DiMS library.
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '2.0'
__date__    = 'April 17th, 2007'

import copy

class Item:
  """ 
  A simple resolution struct that allows for dependency solving.  Has two
  significant fields, 'provides' and 'requires', which act in a simliar way
  to the 'Provides:' and 'Requires:' fields in an RPM spec file.  Also has
  an 'enabled' flag.
  """
  def __init__(self, provides=[], requires=[], enabled=True,
               conditional_requires=[]):
    self.provides = provides
    self.requires = requires
    self.enabled = enabled
    self.conditional_requires = conditional_requires

def resolve(nodes):
  """ 
  Attempt to completely resolve dependencies given the current Item set.  Uses
  the following algorithm:
  
  For each Item that is not yet resolved, examine its requires list.  Iterate
  from left to right over the resolved list, examining the provided elements at
  each index.  As soon as all requirements are matched, the subsequent index
  is the earliest point in the resolved list that the unresolved Item could be
  added.  If all requirements are met, remove Item from the unresolved list and
  add it to the resolved list in the earliest position possible (not already
  occupied) and run resolve() again.  If not all requirements are met, pass for
  now.
  
  If, when the process completes, there are still Items in the unresolved list,
  full dependency resolution is impossible; this raises an UnresolvableError
  exception.  Otherwise, return the resolved list of dependencies.
  """
  if len(nodes) == 0: return
  
  resolved = []
  provides = []
  
  all_provs = []
  # pad resolved and provides to be len(nodes) in size, but empty
  # also make a list of all provides
  for node in nodes:
    resolved.append(None)
    provides.append([])
    
    for prov in node.provides:
      if prov not in all_provs: all_provs.append(prov)
  
  # parent requirement are assumed as provided to the children
  if nodes[0].parent is not None:
    provides[0] = copy.copy(nodes[0].parent.requires)
  
  return _resolve(nodes, resolved, provides, all_provs)

def _resolve(unresolved, resolved, provides, all_provs):
  "'Recursively' resolve all nodes in unresolved"
  for node in unresolved:
    # try to resolve node requires in resolved
    # min_index is the earliest the node could occur in the ordering
    
    # construct a list of meaningful conditional requires
    # (those that are actually provided)
    conds = [ n for n in node.conditional_requires if n in all_provs ]
    
    try:
      min_index = check_requires(node.requires + conds, provides, 0)
    except UnresolvableError:
      continue
     
    # if we get this far, all node requirements were resolved
    j = min_index; added = False
    while j < len(resolved):
      if resolved[j] is None: # only add to empty slots
        resolved[j] = node
        provides[j].extend(node.provides)
        unresolved.remove(node)
        added = True; break
      j += 1
    if not added: raise IndexError # this should never happen
    _resolve(unresolved, resolved, provides, all_provs) # new item added, do another cycle
  
  if len(unresolved) > 0:
    raise UnresolvableError, unresolved
  
  return resolved

def check_requires(reqs, provides, min_index=0):
  for req in reqs:
    found = False
    try:
      for i in range(0, len(provides)):
        min_index = max(min_index, i+1)
        if req in provides[i]:
          found = True; raise StopIteration
      if not found:
        raise UnresolvableError
    except StopIteration:
      continue
  
  return min_index
  

class UnresolvableError(StandardError): pass
