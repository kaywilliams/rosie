import re

__all__ = ['_deformat', '_sort', '_highest', '_lowest', 'Token', 'TokenGroup']

# HELPER FUNCTIONS
def _deformat(s, delims):
  "Create a TokenGroup from a string"
  def _split(s, i):
    if i < len(delims):
      r = TokenGroup(delims, i)
      for l in (s or '').split(delims[i]):
        r.append(_split(l,i+1))
    else:
      r = Token(s)
    return r

  return _split(s, 0)

def _sort(list):
  "Sort a list of strings utilizing the pairwise capabilities of this module."
  if len(list) > 10:
    list = _mergesort(list)
  else:
    list = list[:] # copy list because insertionsort is in place
    _insertionsort(list)
  return list

def _highest(list):
  "Get the highest item from list"
  return _get_hi_lo(list, 1)

def _lowest(list):
  "Get the lowest item from list"
  return _get_hi_lo(list, -1)

def _get_hi_lo(l,v):
  """Get the highest or lowest item from l, as determined by the value of v;
  1 means get highest, -1 means get lowest (identical to the result of cmp
  on two items)"""
  if v not in [-1, 1]:
    raise ValueError, "Invalid comparison value '%s'" % val
  r = l[0]
  for i in l:
    if i.__cmp__(r) == v: r = i
  return r

def _insertionsort(list):
  "Insertion sort implementation for a list.  This is an in-place algorithm."
  for i in range(0, len(list)):
    _insertionsort_helper(i, list, list[i])

def _insertionsort_helper(i,N,v):
  i -= 1
  while i >= 0:
    if N[i] > v:
      N[i+1] = N[i]
      i -= 1
    else: break
  N[i+1] = v


def _mergesort(N):
  "Mergesort implementation for a list.  This algorithm is not in-place"
  if len(N) <= 1: return N
  else:
    mid = len(N)/2
    left  = _mergesort(N[0:mid])
    right = _mergesort(N[mid:len(N)]) # slicing caused problems here
    return _mergesort_merge(left,right)

def _mergesort_merge(l,r):
  "Merge helper function"
  res = []
  while len(l) > 0 and len(r) > 0:
    if l[0] <= r[0]:
      res.append(l.pop(0))
    else:
      res.append(r.pop(0))
  if len(l) > 0:
    res.extend(l)
  if len(r) > 0:
    res.extend(r)
  return res

# CLASSES
class Token(list):
  SPLITRE = re.compile('([0-9]*)')
  def __init__(self, s):
    i = 0
    input = []
    for token in self.SPLITRE.split(s):
      if token:
        if i % 2: # odd indexes are integers
          input.append(IntegerToken(token))
        else: # even indexes are strings
          input.append(StringToken(token))
      i += 1
    list.__init__(self, input)

  def __str__(self):
    return ''.join([ str(x) for x in self ])
  def __repr__(self):
    return 'Token(\'%s\')' % self.__str__()

  def __cmp__(self, other):
    if not isinstance(other, Token):
      raise TypeError, (type(self), type(other))
    for (a,b) in map(None, self, other):
      if a and not b:
        return 1
      elif b and not a:
        return -1
      else:
        r = cmp(a,b)
        if r: return r
        else: continue
    return 0


class StringToken(str):
  "Handles sorting for strings"
  def __cmp__(self, other):
    "String tokens force string comparison, regardless of other class"
    if isinstance(other, StringToken) or isinstance(other, IntegerToken):
      return cmp(str(self), str(other))
    else:
      raise TypeError

class IntegerToken(int):
  "Handles sorting for integers"
  def __cmp__(self, other):
    "Integer tokens use int comparison if both args are ints, otherwise string"
    if isinstance(other, self.__class__):
      return int.__cmp__(self, other)
    elif isinstance(other, StringToken):
      return cmp(str(self), str(other))
    else:
      raise TypeError

class TokenGroup(list):
  def __init__(self, delims, level=0):
    self.delims = delims
    self.level = level
    list.__init__(self)

  def __cmp__(self, other):
    if not isinstance(other, self.__class__):
      if isinstance(other, str):
        other = _deformat(other, delims=self.delims)
      else:
        raise TypeError

    for (a,b) in map(None, self, other):
      if a and not b:
        return 1
      elif b and not a:
        return -1
      else:
        r = cmp(a,b)
        if r: return r
        else: continue
    return 0

  def __repr__(self):
    return "TokenGroup(%s)" % list.__repr__(self)
  def __str__(self):
    return self.reformat()

  def reformat(self):
    "Convert a TokenGroup back into a string"
    s = ''
    delim = self.delims[self.level]
    for t in self:
      if isinstance(t, TokenGroup):
        s += t.reformat() + delim
      else:
        s += str(t) + delim
    else:
      s = s.rstrip(delim) # get rid of the last delim we add
    return s
