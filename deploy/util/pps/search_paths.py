#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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
search_paths.py - a handler for setting default search_paths for use during
pps path initialization.
"""

from errno import ENOENT
import itertools 
import re

import deploy.util

from functools import wraps
from os import strerror as os_strerror

from deploy.util.pps import path as _orig_path

MACRO_PATTERN = re.compile('%{(?:(?!%{).)*?}') # match inner macros - nested
                                               # macros not allowed in search
                                               # paths for now

class SearchPathsHandler(object):
  """
  A handler that wraps the deploy.util.pps.path method to provide a default
  search_paths attribute.

  SearchPathHandlers have a single attribute:
   * search_paths:  Dictionary of search paths passed to the
                    deploy.util.pps.path method. See the deploy.util.pps.path
                    method for more information on the search_paths attribute.

  SearchPathHandler instances wrap (decorate) calls to deploy.util.pps.path()
  to provide the search_paths attribute. To stop path objects from using the
  default search_paths, call the unwrap_path() method. If multiple pps
  handlers (i.e. CacheHandler and SearchPathsHandler) are being used, they must
  be unwrapped in the reverse order that they were wrapped to achieve the
  desired result.
  """
  def __init__(self, search_paths={}):
    self.search_paths = search_paths

    self.wrap_path()
    self.wrap_error()

  def wrap_path(self):
    "wrap deploy.util.pps.path function to set this instance's search_paths "
    "as the search_paths attribute for new path instances"
    setattr(deploy.util.pps, 'path', 
            self.path_wrapper(getattr(deploy.util.pps, 'path')))

  def unwrap_path(self):
    "restore original deploy.util.pps.path function"
    setattr(deploy.util.pps, 'path', _orig_path)

  def wrap_error(self):
    "wrap deploy.util.pps.Path.PathError.__init__ function to provide "
    "informative 'file not found' errors"
    obj = deploy.util.pps.Path.PathError
    setattr(obj, '__init__', self.error_wrapper(getattr(obj, '__init__')))

  def path_wrapper(self, fn):
    @wraps(fn)
    def wrapped(string, search_paths = {}, search_path_ignore = [], 
                *args, **kwargs):
      """
      Evaluates two arguments:
       * search_paths - a dict of search paths in 'placeholder: string or list'
         format, for example:

         { '%{templates-dir}' : '/usr/share/deploy/templates' }
         { '%{templates-dir}' : [ '/etc/deploy/templates',
                                  '/usr/share/deploy/templates' ] }

         Checks if one or more placeholder is in the provided string. If
         so, iterates through a list of (placeholder, value) combinations,
         testing the resulting string at each pass to see if a file of that
         name file. If a match is found, processing stops and a Path with the
         resulting string is returned. Else, a Path to the original string is
         returned.

       * search_path_ignore - a string or list of strings to ignore when
         resolving search paths. If a resolved string matches an item in the
         list, it is ignored and the search for a match continues.
      """

      if isinstance(string, deploy.util.pps.Path.BasePath):
        return string
      elif string is None:
        return None

      search_paths.update(self.search_paths)

      # attempt to resolve macros, if found
      found_macros = []
      for macro in (MACRO_PATTERN.findall(string) or []):
        if macro in search_paths: found_macros.append(macro)

      if found_macros:
        if isinstance(search_path_ignore, basestring): 
          search_path_ignore=[ search_path_ignore ]
        search_path_ignore = [ str(x) for x in search_path_ignore ]

        macro_tuples = [] 
        for macro in found_macros:
          values = search_paths[macro]
          if isinstance(values, basestring): values = [ values ]
          macro_tuples.append( [ (macro, v) for v in values ] )

        for item in itertools.product(*macro_tuples):
          new_strings = [ (string[:], '') ] # initial (string, ending) tuple
          _add_strings_with_unbalanced_endings(string, new_strings, ending='')
          for new_string, ending in new_strings:
            for macro, value in item:
              new_string = new_string.replace(macro, value)
            if new_string in search_path_ignore:
              continue
            pathobj = deploy.util.pps._path(new_string, *args, **kwargs)
            if pathobj.exists():
              pathobj.search_paths = search_paths
              return pathobj + ending
          
      # if no macros, or if macros could not be resolved, return a path
      # with the initial string, with the search_paths attribute set
      path = fn(string, *args, **kwargs)
      path.search_paths = search_paths
      return path
    return wrapped

  def error_wrapper(self, fn):
    @wraps(fn)
    def wrapped(self, errno, filename=None, strerror=None, *args, **kwargs):
      if (isinstance(filename, deploy.util.pps.Path.BasePath) and
          errno == ENOENT): # file not found
          if not strerror: strerror = ''
          strerror = (strerror + ' ' + get_search_path_errors(filename)
                     ).lstrip()
      return fn(self, errno, filename, strerror, *args, **kwargs)
    return wrapped

def _add_strings_with_unbalanced_endings(string, new_strings, ending):
  """ 
  If string ends with the character '")] or } and it does not have a matching
  beginning character, strip the ending character recursively and return a list
  of tuples with base strings and stripped endings. This allows us to handle
  paths that are part of arbitrary scripts, e.g. "$(cat
  %{templates-dir}/%{norm-os}/some/path)"
  """
  if (string.endswith("'") and string.count("'")%2 != 0 or
      string.endswith('"') and string.count('"')%2 != 0 or
      string.endswith(')') and string.count('(') - string.count(')') != 0 or
      string.endswith(']') and string.count('[') - string.count(']') != 0 or
      string.endswith('}') and string.count('{') - string.count('}') != 0):
    ending = string[-1] + ending
    new_strings.append( (string[:-1], ending) )
    _add_strings_with_unbalanced_endings(string[:-1], new_strings, ending)

  return new_strings

def get_search_path_errors(path):
  "check path for search_path errors and returns an error string if found"
  message = "%s: %s" % (os_strerror(ENOENT), path)
  if hasattr(path, 'search_paths'):
    lines = []
    for k,v in path.search_paths.items():
      if k in path:
        lines.append('\n\n%s:' % k)
        lines.extend([ path.replace(k, x) for x in v ])
    if lines:
      message += ". The following paths were searched:"
      message += '\n'.join(lines)
  else: 
    message += ":"
  
  return message
