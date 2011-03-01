#
# Copyright (c) 2011
# Rendition Software, Inc. All rights reserved.
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
import re
import stat
import time

from systemstudio.util import statfmt

QFIND = re.compile('(?:\'[^\']*\')|(?:\"[^\"]*\")')

CTIME_PFMT='%a %b %d %I:%M:%S %Y'

class Path_Printf(object):
  "Print formatting functions for Path objects"

  def __mod__(self, arg):
    return self.__class__(str.__mod__(self, arg))

  def printf(self, format='%p'):
    """
    formats:
      %%  - literal percent sign
      %a  - access time
      %Ak - access time according to format k (either '@' or strftime string)
      %b  - disk space usage in 512-byte blocks (not supported yet)
      %c  - change time
      %Ck - change time according to format k (same as %A)
      %f  - basename
      %G  - group id
      %h  - dirname
      %i  - inode number
      %k  - disk space usage in 1K blocks (not supported yet)
      %l  - object of symbolic link; empty string if not a symbolic link
      %m  - permission bits (octal)
      %M  - permission bits (symbolic form)
      %n  - number of hard links to file
      %p  - full filename
      %P  - filename without dir prefix
      %s  - size in bytes
      %t  - modify time
      %Tk - modify time according to format k (same as %A)
      %U  - user id

    Format modifiers that require additional argument passing (indicated
    by a 'k' following their character) support a slightly extended method
    that allows passing more than a single character each time.  If one of
    these characters (currently 'A', 'T', and 'U') is followed immediately
    by a ' or " character, then each character up until the next matching
    ' or ", respectively, is passed as an argument.  For example, the
    following format string

      %A'%Y %m %d %H:%M:%S' %f

    passes the string '%Y %m %H:%M:%S' to the _printf_A() function.  This
    same thing is possible in the older syntax, but in a potentially more
    verbose manner:

      %AY %Am %Ad %AH:%AM:%AS %f

    The above also results in 6 calls to _printf_A() instead of just 1.
    """
    ret = ''
    infmt = False
    i = 0; j = len(format)
    while i < j:
      char = format[i]
      if not infmt:
        if char == '%':
          infmt = True
        else:
          ret += char
      else:
        if char != '%' and not hasattr(self, '_printf_%s' % char):
          raise ValueError("Invalid format character '%%%s' at position %d" % (char, i))

        if char == '%': # literal percent
          ret += char

        elif char in 'ACT': # printf() with args
          i += 1
          if format[i] == '\"' or format[i] == '\'':
            match = QFIND.match(format[i:])
            try:
              args = match.group()
              length = match.span()[1] - 1
            except AttributeError:
              raise ValueError("Missing closing \" or \' to match character at position %d" % i)
            i += length
          else:
            args = '%%%s' % format[i] # insert % sign in front for compat
          ret += eval('self._printf_%s(\'%s\')' % (char, args))

        else: # printf() without args
          ret += eval('self._printf_%s()' % char)
        infmt = False
      i += 1
    return ret

  # printf internal formatting functions
  def _printf_a(self):
    return self._printf_A(CTIME_PFMT)
  def _printf_A(self, k):
    return time.strftime(k, time.localtime(self.atime))
  ##def _printf_b(self):
  def _printf_c(self):
    return self._printf_C(CTIME_PFMT)
  def _printf_C(self, k):
    return time.strftime(k, time.localtime(self.ctime))
  def _printf_f(self):
    return self.basename
  def _printf_G(self):
    return str(self.stat().st_gid)
  _printf_g = _printf_G
  def _printf_h(self):
    return self.dirname
  def _printf_i(self):
    return str(self.stat().st_ino)
  ##def _printf_k(self):
  def _printf_l(self):
    if self.islink():
      return self.readlink()
    else:
      return ''
  def _printf_m(self):
    mode = self.stat().st_mode
    if not mode: return ''
    else: return str(oct(mode))[1:] # remove leading 0
  def _printf_M(self):
    mode = self.stat().st_mode
    if not mode: return ''
    return statfmt.format(mode)
  def _printf_n(self):
    return str(self.stat().st_nlink)
  def _printf_p(self):
    return self
  def _printf_s(self):
    return str(self.size)
  def _printf_t(self):
    return self._printf_T(CTIME_PFMT)
  def _printf_T(self, k):
    return time.strftime(k, time.localtime(self.mtime))
  def _printf_U(self):
    return str(self.stat().st_uid)
  _printf_u = _printf_U
