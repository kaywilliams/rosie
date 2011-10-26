Test methods of PathToken

Set up the environment
  >>> from centosstudio.util import pps
  >>> P = pps.Path.%(pathtype)s.%(pathcls)s
  >>> absolute = P('%(abspath)s') / '%(relpath)s'
  >>> relative = P('%(abspath-noroot)s') / '%(relpath)s'

Index operations: p[0] returns the root of absolute paths or the first element
of relative paths.  p[-1] returns the last element (basename)
  >>> t = absolute.splitall()
  >>> t[0]
  %(pathcls)s('%(root)s')
  >>> t[-1] 
  %(pathcls)s('%(relpath-basename)s')
  >>> t[2]
  %(pathcls)s('%(abspath-basename)s')
  >>> t = relative.splitall()
  >>> t[0]
  %(pathcls)s('a')
  >>> t[-1]
  %(pathcls)s('%(relpath-basename)s')
  >>> t[2]
  %(pathcls)s('%(relpath-dirname)s')

Slice operations: p[0:1] returns the root of absolute paths, the first item
of relative paths; p[0:2] returns the root and first element of absolute
paths, the first 2 elements of relative paths, etc.  p[:-1] returns all but
the last element of a path (dirname); p[1:] returns all but the root of
absolute paths and all but the first element of relative paths.  All paths
returned are normalized, meaning that p[0:len(p)] may not be the same string
as p (though they will still be equivalent paths).  The type of the Path
object returned is the same as the original, even if it doesn't have a root.
  >>> t = absolute.splitall()
  >>> t[0:len(t)]
  %(pathcls)s('%(abspath)s%(sep)s%(relpath)s')
  >>> t[1:]
  %(pathcls)s('%(abspath-noroot)s%(sep)s%(relpath)s')
  >>> t[:-1]
  %(pathcls)s('%(abspath)s%(sep)s%(relpath-dirname)s')
  >>> t[1:-1]
  %(pathcls)s('%(abspath-noroot)s%(sep)s%(relpath-dirname)s')
  >>> t = relative.splitall()
  >>> t[0:len(t)]
  %(pathcls)s('%(abspath-noroot)s%(sep)s%(relpath)s')
  >>> t[1:]
  %(pathcls)s('%(abspath-basename)s%(sep)s%(relpath)s')
  >>> t[:-1]
  %(pathcls)s('%(abspath-noroot)s%(sep)s%(relpath-dirname)s')
  >>> t[1:-1]
  %(pathcls)s('%(abspath-basename)s%(sep)s%(relpath-dirname)s')
