Test posix methods of path objects

Set up the environment
  >>> from deploy.util import pps
  >>> P = pps.Path.%(pathtype)s.%(pathcls)s 
  >>> absolute = P('%(abspath)s')
  >>> relative = P('%(relpath)s')

Path.__div__ performs path joining as if each argument were a separate 
directory or file.  If the second argument is an absolute path, the 
first argument is ignored.  If the second argument is a string, it is 
converted into a path for joining.  Each argument is preserved exactly 
as is, with one '%(sep)s' added between the two if the first argument does not 
end in one.
  >>> absolute / relative
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')
  >>> relative / relative
  %(pathcls)s('%(relpath)s%(sep)s%(relpath)s')
  >>> absolute+'%(sep)s%(sep)s' / relative+'%(sep)s%(sep)s'
  %(pathcls)s('%(abspath)s%(sep)s%(sep)s%(relpath)s%(sep)s%(sep)s')
  >>> absolute / absolute
  %(pathcls)s('%(abspath)s')
  >>> absolute / '%(relpath)s'
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')

Path.__floordiv__ is the same as Path.__div__ with the exception that the
second argument is always intepreted as a relative path, even if it is actually
absolute.  This means that the root is removed before joining (usually
everything up to the first 'relative part' path separator for absolute paths,
nothing for relative paths).
  >>> absolute // relative
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')
  >>> relative // relative
  %(pathcls)s('%(relpath)s%(sep)s%(relpath-noroot)s')
  >>> absolute+'%(sep)s%(sep)s' // relative+'%(sep)s%(sep)s'
  %(pathcls)s('%(abspath)s%(sep)s%(sep)s%(relpath-noroot)s%(sep)s%(sep)s')
  >>> absolute // absolute
  %(pathcls)s('%(abspath)s%(sep)s%(abspath-noroot)s')
  >>> absolute // '%(relpath)s'
  %(pathcls)s('%(abspath)s%(sep)s%(relpath-noroot)s')

Path.__rdiv__ allows a string to be __div__'d with a Path object.  It otherwise
has the same behavior as Path.__div__
  >>> '%(abspath)s' / relative
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')
  >>> '%(abspath)s' / absolute
  %(pathcls)s('%(abspath)s')
  >>> '%(abspath)s%(sep)s%(sep)s' / relative+'%(sep)s%(sep)s'
  %(pathcls)s('%(abspath)s%(sep)s%(sep)s%(relpath)s%(sep)s%(sep)s')

Path.__rfloordiv__ allows a string to be __floordiv__'d with a Path object.
It otherwise has the same behavior as Path.__floordiv__
  >>> '%(abspath)s' // relative
  %(pathcls)s('%(abspath)s%(sep)s%(relpath-noroot)s')
  >>> '%(abspath)s' // absolute
  %(pathcls)s('%(abspath)s%(sep)s%(abspath-noroot)s')
  >>> '%(abspath)s%(sep)s%(sep)s' // relative+'%(sep)s%(sep)s'
  %(pathcls)s('%(abspath)s%(sep)s%(sep)s%(relpath-noroot)s%(sep)s%(sep)s')

Path.joinpath allows multiple paths to be joined together in a single
operation.  It accepts both Paths and strings as arguments.  As with
__div__, an absolute path will override any previous arguments.  (There
currently is no equivalent for the __floordiv__ operator.)
  >>> absolute.joinpath(relative, '%(relpath)s', relative)
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s%(sep)s%(relpath)s%(sep)s%(relpath)s')
  >>> absolute.joinpath('%(relpath)s', absolute, relative)
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')

NOTE - The following two algorithms (basename and dirname) perform path
normalization on their output.  Its possible that this isn't desired behavior
(the unix utiliities don't do this); we may want to investigate this in the
future.

Path.basename is set to the final element in a path, per the unix basename
utility (with the very likely exception of some wierd corner cases that I'm
unaware of).  Unlike some versions of basename, it does not suffer from the
weakness of trailing slashes throwing off its result.  (NOTE - this means
that its behavior is different than os.path.basename())
  >>> absolute.basename
  %(pathcls)s('%(abspath-basename)s')
  >>> relative.basename
  %(pathcls)s('%(relpath-basename)s')
  >>> P('%(root)s').basename
  %(pathcls)s('%(root)s')
  >>> (absolute+'%(sep)s%(sep)s').basename
  %(pathcls)s('%(abspath-basename)s')

Path.dirname is set to the full path minus the basename, per the unix dirname
utility (again with the likely exception of weird corner cases I don't know
about).  As with basename, it is not sensitive to trailing slash related
issues and as such differs with the behavior of os.path.dirname()
  >>> absolute.dirname
  %(pathcls)s('%(abspath-dirname)s')
  >>> relative.dirname
  %(pathcls)s('%(relpath-dirname)s')
  >>> P('%(root)s').dirname
  %(pathcls)s('%(root)s')
  >>> (absolute+'%(sep)s%(sep)s').dirname
  %(pathcls)s('%(abspath-dirname)s')

Path.isabs() returns True if the path is an absolute path (has a root), False
otherwise.
  >>> absolute.isabs()
  True
  >>> relative.isabs()
  False

Path.abspath() returns an absolute Path of the given Path.  If the Path is
already absolute (has a root) then this has no effect; if it is relative,
non-local paths raise an exception while local paths are joined onto the
current working directory and returned.
#>>> relpath.abspath() # can't test this automatically yet
#%(pathcls)s('%%(relpath-absolute)s')
  >>> absolute.abspath()  
  %(pathcls)s('%(abspath)s')

Path.normcase() returns the Path object with its case normalized.  The result
of this is dependent on the path type; some path types are case sensitive
while others are not.  All protocol/realms are normalized the same, however,
since they are not case-sensitive.
# actually thats not totally true; the netloc of mirror paths might be case-
# sensitive since it is any valid path object iteself...
# individual path normalization must happen per path type
  >>> P('%(root)s').normcase()
  %(pathcls)s('%(root)s')
  >>> P('%(root)s'.upper()).normcase()
  %(pathcls)s('%(root)s')

Path.normpath() returns a normalized version of the Path object, handling the
following normalizations:
1) Replaces all occurances of multiple '%(sep)s' with a single '%(sep)s'
   for all separators in the 'heirarchical part' of the path (not the root).
2) Resolves any curdir ('%(curdir)s') and pardir ('%(pardir)s') arguments.
Individual path types may have additional normalizations to perform.
# individual normalization stuff
  >>> absolute.normpath()
  %(pathcls)s('%(abspath)s')
  >>> (absolute+'%(sep)s%(sep)s' / relative+'%(sep)s%(sep)s').normpath()
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')
  >>> (absolute / '%(pardir)s' / relative / '%(curdir)s').normpath()
  %(pathcls)s('%(abspath-dirname)s%(sep)s%(relpath)s')

Path.relpathto() returns a Path object representing the relative path from
the Path to the given argument.  If the two paths share no common ancestors,
including their root, the result is the original argument; otherwise, it is
the set of curdirs ('%(curdir)s'), pardirs ('%(pardir)s'), and path elements that
need to be followed to get from the path to the argument.  Calling relpathto
on a path with the same path as the argument will return curdir ('%(curdir)s').
  >>> P('%(root)stmp').relpathto('%(abspath)s')
  %(pathcls)s('%(pardir)s%(sep)s%(abspath-noroot)s')
  >>> P('%(root)stmp').relpathto('%(root)stmp%(sep)s%(abspath-noroot)s')
  %(pathcls)s('%(abspath-noroot)s')
  >>> absolute.relpathto(absolute)
  %(pathcls)s('%(curdir)s')

Path.relpathfrom() returns a Path object representing the relative path from
the given argument to the Path.  It is the inverse of Path.relpathto() (in
fact, Path.relpathto() is implemented as pps.path(arg).relpathto(Path))
  >>> absolute.relpathfrom(P('%(root)stmp'))
  %(pathcls)s('%(pardir)s%(sep)s%(abspath-noroot)s')
  >>> P('%(root)stmp%(sep)s%(abspath-noroot)s').relpathfrom(P('%(root)stmp'))
  %(pathcls)s('%(abspath-noroot)s')
  >>> absolute.relpathfrom(absolute)
  %(pathcls)s('%(curdir)s')

Path.equivpath() returns True if the argument represents an equivalent Path.
The definition of equivalent is somewhat path type dependant; however, for
most paths, paths are normalized and compared.
  >>> absolute.equivpath(absolute)
  True
  >>> absolute.equivpath(relative)
  False
  >>> absolute.equivpath(P('%(abspath-noroot)s'))
  False
  >>> relative.equivpath(P('%(relpath-noroot)s'))
  True
  >>> (absolute / relative).equivpath(P('%(abspath)s%(sep)s%(sep)s%(sep)s%(relpath)s'))
  True
  >>> absolute.equivpath(absolute.touri())
  True

Path objects define a number of read-only attributes that are parsed out of
the string given as the input.  These include protocol (scheme), realm (netloc),
path, params, query, fragment, username, password, hostname, port, and root.
They are extracted from the path object on the assumption that they match the
following format:

  Path     : <root>[<path>]
  <root>   : [<scheme>:[//<netloc>]]/
  <netloc> : [<username>[:<password>]@]<hostname>[:<port>]
  <path>   : <heirarchical part>[[[;<params>]?query]#fragment]

where <netloc> everything from username through port, inclusive, and <root> is
everything from scheme through port, inclusive.  All of them (except for path)
return None if unknown (such as in the case of relative paths of any type).
# add some params, query, fragment test cases; they all return None now
  >>> absolute.touri().protocol
  '%(scheme)s'
  >>> absolute.touri().realm
  '%(netloc)s'
  >>> absolute.touri().path
  %(pathcls)s('%(abspath-noroot)s')
  >>> absolute.touri().params
  >>> absolute.touri().query
  >>> absolute.touri().fragment
  >>> absolute.touri().username
  >>> absolute.touri().password
  >>> absolute.touri().hostname
  '%(netloc)s'
  >>> absolute.touri().port
  >>> absolute.root
  %(pathcls)s('%(root)s')
  >>> relative.root
