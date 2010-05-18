"""
permute.py

Defines a simple syntax for iterating over a subset of a matrix of values.

The basic syntax of a filter is:

  filter     ::= tokenset (';' tokenset)*
  tokenset   ::= token (' ' token)*
  token      ::= identifier '=' qualifier
  qualifier  ::= index (',' index)*
  index      ::= (glob|[modifier]identifier)
  glob       ::= '*'
  modifier   ::= ('+'|'-')

  identifier ::= (letter|'_')(letter|digit|'_')*
  letter     ::= lowercase|uppercase
  lowercase  ::= 'a'...'z'
  uppercase  ::= 'A'...'Z'
  digit      ::= '0'...'9'

That is, a filter consists of one or more token sets, separated by ';', and
a token set consists of one or more tokens, separated by ' '.  A token, in
this context, takes the form of 'x=y' where x is any valid Python identifier
and y is one or more indexes, separated by ','.  An index is either a glob
('*') or any valid Python identifier optionally prefixed by a modifier ('+'
or '-').

Examples:
a=1
a=1,fu b=* c=bar
a=1,2,3 b_1=*; t1=+hello,-goodbye

A token set describes a subset of a potentially nested table of values.
When iterating over a nested table using a filter, a specific item will be
returned if the token set contains at least one token that references that
item.  This is perhaps best demonstrated by an example:

Example - a 2-level nested table

distros  = ['fedora', 'redhat', 'centos']
versions = ['5', '6', '7']
archs    = ['i386', 'x86_64']

>>> D = dict(d=distros, v=versions, a=archs)

>>> for i in permute(D, 'd=fedora v=5,6,7'): print i
('fedora', '5')
('fedora', '6')
('fedora', '7')
>>> for i in permute(D, 'd=fedora v=*; d=redhat v=6'): print i
('fedora', '5')
('fedora', '6')
('fedora', '7')
('redhat', '6')
>>> for i in permute(D, 'd=fedora v=5; d=redhat v=6; d=centos v=7'): print i
('fedora', '5')
('redhat', '6')
('centos', '7')
>>> for i in permute(D, 'd=fedora v=*,-6; d=centos v=6'): print i
('fedora', '5')
('fedora', '7')
('centos', '6')

The filter system will work for nested tables of any degree.  Each
degree of the source table allows an additional token to be specified
per token group; for example, if the above table were crossed with
arch = ['i386', 'x86_64'], filters on the resulting nested
table could have an additional token referring to the arch:

>>> E = dict(d=distros, v=versions, a=archs)

>>> for i in permute(E, 'd=fedora v=*,-6 a=i386'): print i
('fedora', '5', 'i386')
('fedora', '7', 'i386')
>>> for i in permute(E, 'd=fedora v=* a=*'): print i
('fedora', '5', 'i386')
('fedora', '5', 'x86_64')
('fedora', '6', 'i386')
('fedora', '6', 'x86_64')
('fedora', '7', 'i386')
('fedora', '7', 'x86_64')

Note that the identifier preceding the '=' in a token corresponds directly
to the identiefier used in creating the Matrix object.  In the above example,
the 'd' identifier refers to items in the distros list, the 'v' to the
versions list, and the 'a' to the archs list.

The modifiers '+' and '-' interact with the default filter set in the
following way.  The '+' indicates additive modification, meaning that the
identifier that follows it should be added to the default set for that list.
If the item added is not in the default set, it is appended to the returned
list.  Conversely, the '-' indicates subtractive modification, meaning that
the identifier that follows it should be removed from the default set for
that list.  If the item removed is not in the default set, it is ignored.
If an identifier is not preceded by a modifier, then the default set for the
list is discarded entirely and the identifier itself is used.

For example:

>>> F = dict(d=distros)

>>> for i in permute(F, 'd=-centos'): print i
('fedora',)
('redhat',)
>>> for i in permute(F, 'd=centos'): print i
('centos',)
>>> for i in permute(F, 'd=+suse,-centos'): print i
('fedora',)
('redhat',)
('suse',)

If any index in the identifier doesn't contain a modifier, the entire default
set will be discarded, regardless of whether other indexes have modifiers.
In these cases, the unmodified indexes essentially form the new default set
that modified indexes affect.

Notes

The order of tokens in a tokenset effects the order of the values in the
final returned tuple(s).  Thus, while a permute of 'd=centos v=5,6' and
'v=5,6 d=centos' are similar in that they both cover all permutations of
'centos' and '5' and '6', they do so in a different order (the first would
return ('centos','5'),('centos','6'), while the second ('5','centos'),
('6','centos').

# TODO - the following gotchas could probably be resolved through
# intelligent handling of filters, though it would be somewhat complex
If two tokensets in the same filter have a different number of tokens, the
returned tuples will have different lengths.

Similarly, if two tokensets are the same length but have a different
ordering of tokens, the returned tuples will have different meanings at a
given index.

Finally, if two tokensets end up indexing the same item more than once, it
will appear in the final output more than once as well.
"""

import re

try:
  from solutionstudio.util.listfmt import ListFormatter
  _LISTFMT = ListFormatter(pre='\'', post='\'', sep=', ')
  def listfmt(l, *args, **kwargs): return _LISTFMT.format(l)
except ImportError:
  def listfmt(l, *args, **kwargs): return str(l)

# either +<item>, -<item>, or <item>
# RE_ITYPE.match('+<item>').groups() = ('<item>',None,None)
# RE_ITYPE.match('-<item>').groups() = (None,'<item>',None)
# RE_ITYPE.match('<item>').groups()  = (None,None,'<item>')
RE_ITYPE = re.compile('(?:\+(.*))|(?:\-(.*))|(.*)')

RE_SORT_ORDER = re.compile('(?:([\w]+)=[^\s]*)*')

FILTER_SPLIT    = re.compile('[\s]*;[\s]*') # regex for splitting filters into tokensets
TOKENSET_SPLIT  = re.compile('([a-zA-Z_][\w]*)=([^\s]+)') # regex for splitting tokens into identifier, qualifier pair
QUALIFIER_SPLIT = re.compile('[\s]*,[\s]*') # regex for splitting qualifiers

def permute(table, f=None, order=None):
  assert (table is None or isinstance(table, dict))
  return flatten(_process_filter(f or '', default=table, order=order))

# processing methods
def _process_filter(f, default=None, order=None):
  r = [] # return list

  tokensets = []
  for tokenset in filter(None, FILTER_SPLIT.split(f)):
    tokensets.append((tokenset, _process_tokenset(tokenset, default=default)))

  order, length = _check_tokensets(tokensets, order=order)

  for _,tsdata in tokensets:
    _d = {} # temporary data storage
    for id, qs in tsdata:
      _d[id] = qs # store qualifiers by id

    args = []
    for id in order: # sort qualiifers by id
      try:
        args.append(_d[id])
      except KeyError:
        # if not found, assume '*'
        args.append(_compute_qualifiers('*', default=(default or {}).get(id, [])))

    r.append(crossproduct(*args))

  return r

def _check_tokensets(tokensets, order=None, length=None):
  # ensure token sets are of the same length and have the same token order
  order_supplied = order is not None # only check order if not supplied

  for (ts, tsdata) in tokensets:
    # check length
    if not order_supplied:
      if length is None:
        length = len(tsdata)
      else:
        if len(tsdata) != length:
          raise ValueError("Token set '%s' has an incorrect number of tokens: "
                           "expected %d, got %d" % (ts, length, len(tsdata)))

    ids = [ t[0] for t in tsdata]

    # check names
    if order is None:
      order = ids
    else:
      s_order = set(order)
      s_ids   = set(ids)

      if not s_ids <= s_order:
        raise ValueError("Extra identifier%s in token set '%s': %s; expected: %s" %
                         (len(s_ids - s_order) != 1 and 's' or '',
                          ts,
                          listfmt(list(s_ids - s_order)),
                          listfmt(order)))
      ##elif not s_order <= s_ids:
      ##  raise ValueError("Missing identifier%s in token set '%s': %s; expected: %s" %
      ##                   (len(s_order - s_ids) != 1 and 's' or '',
      ##                    ts,
      ##                    listfmt(list(s_order - s_ids)),
      ##                    listfmt(order)))

    # check order if order was not explicity supplied
    if not order_supplied:
      if [ t[0] for t in tsdata ] != order:
        raise ValueError("Incorrect token ordering for token set '%s': "
                         "expected %s, got %s" % (ts, order, ids))

  return order, length

def _process_tokenset(tokenset, default=None):
  "[(id1,qs1),(id2,qs2),...] = _process_tokenset(tokenset[,default])"
  return [ (id, _compute_qualifiers(QUALIFIER_SPLIT.split(qs),
                  default=(default or {}).get(id, [])))
           for (id, qs) in TOKENSET_SPLIT.findall(tokenset) ]

def _compute_qualifiers(I, default=None):
  default  = set(default or [])
  s = set(default) # final set
  a = set() # set of explicitly added items
  r = set() # set of explicitly removed items
  for i in I:
    add, sub, rpl = RE_ITYPE.match(i).groups() # add, sub, rpl mut. exclusive
    if add is not None: # +<item>
      s.add(add)
      a.add(add)
    if sub is not None: # -<item>
      s.discard(sub)
      r.add(sub)
    if rpl is not None: #  <item>
      if rpl == '*':
        s = s | (default - r) # add items we haven't removed
      else:
        s.add(rpl)
        a.add(rpl)
        s = s - (default - a) # remove items we haven't added
  return sorted(s)


def crossproduct(iterable, *iterables):
  "Return the crossproduct (of sorts) of the iterables"
  iterables = list(iterables)
  return [ _crossproduct([i], *iterables) for i in iterable ]

def _crossproduct(tup, *iterables):
  if len(iterables) == 0:
    return tuple(tup)
  else:
    iterables = list(iterables)
    iterable  = iterables.pop(0)
    return [ _crossproduct(tup + [i], *iterables) for i in iterable ]

def flatten(l):
  "Flatten a nested list"
  return _flatten(l, [])

def _flatten(l, r):
  for i in l:
    if isinstance(i, list):
      _flatten(i, r)
    else:
      r.append(i)
  return r

distros  = ['fedora','redhat','centos']
versions = ['5','6','7']
archs    = ['i386','x86_64']

D = dict(d=distros,v=versions,a=archs)
