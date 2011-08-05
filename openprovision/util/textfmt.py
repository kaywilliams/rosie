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
"""
textfmt.py

Provides simultaneous right- and left-justification to text blocks.

justify.py can be used to justify text blocks so that they use a uniform
amount of space on the screen.  It is intended as an improvement over the
builtin textwrap module in python in that it avoids the 'ragged-right' edge
that this module typically produces.  It also provides a more flexible
mechanism for dealing with documents that have a somewhat fixed set of
formats without requiring the format to be explicitly defined beforehand
through the use of regular expressions in indent blocks.

Currently, justify is not a complete replacement for textwrap.  In paticular,
it doesn't address some of the edge cases, specifically when a single word
is longer than the requested wrap size (the module will place this word on
its own line).  It also suffers from a few of the same limitations as
textwrap, in particular with regard to some of the locale-insensitive
functionality and inability to reliably detect a sentence ending.
"""

import copy
import random
import re

WHITESPACE = re.compile('[\s]+')

DELIM_LINE = re.compile('(\n)')
DELIM_PARA = re.compile('(\n[\s]*\n)')

# the following regular expression is copied from textwrap and modified slightly
# This regular expression splits up a string into indivisible words suitable for
# wrapping.  For example:
#   "What a cool regex -- it handles -options and hyphenated-words!"
# splits into
#   "What", "a", "cool", "regex", "--", "it", "handles", "-options", "and",
#   "hyphenated-", "words!"
# Each token above is separated by the whitespace that was encountered between
# tokens.
TOKEN_SEP = re.compile(
     r'(\s+|'                                # whitespace
     r'[^\s\w]*\w+[a-zA-z]-(?=\w+[a-zA-Z])|' # words, possibly hyphenated
     r'(?<=[\w\!\"\'\&\.\,\?])-{2,}(?=\w))') # em-dash

class Format:
  "Helper class representing the format of a certain block (paragraph) of text"
  def __init__(self, leading=None, hanging=None, length=None):
    """
    Initialize a format object.  The relevant parameters are:
     * leading : a regular expression denoting the format of the leading indent,
                 if any.  The 'leading indent' of a paragraph is any text that
                 precedes the first line of a paragraph; for example, the leading
                 indent of this paragraph is " * leading : ".  If leading is left
                 at None, then no leading indent is assumed.
     * hanging : a regular expression denoting the format of the hanging indent,
                 if any.  The 'hanging indent' of a paragraph is any text that
                 precedes the second and subsequent lines of a paragraph; for
                 example, the hanging indent of this paragraph is "             ".
                 If hanging is left at None, then no hanging indent is assumed.
     * length :  the length this paragraph should be wrapped to.  If not lenght is
                 specified, typically the functions using this format will use the
                 length explicitly specified in the function call.

    The contents of format.leading and format.hanging are matched against lines in
    a paragraph in order to help preserve formatting.  For example, if an input
    string looks like

      '''1.  There is a lot of information available to you
             from the internet; all you have to do is open
             your eyes to see it.'''

    textwrap would remove all the leading whitespace on subsequent lines by default,
    leaving you with one block of text with no indentation.  You can use the
    'subsequent_indent' argument to specifiy that it should preserve the indentation,
    but this requires that you know the exact number of spaces.  Furthermore, you
    have no flexibility as far as the 'initial_indent' argument is concerned; you
    must know the exact number for each element in a list in order for it to process
    correctly.

    justify handles this differently.  Instead of specifying a string indicating the
    initial and subsequent indents, justify accepts regular expressions.  This
    allows you to specify the above list as leading='^[\d]*\.[\s]+', hanging='^[\s]+',
    which is a fairly flexible representation.  If instead you want the stricter
    version, you could use leading='^\d\.  ', hanging='^    '.  Either would work on
    the above input to produce a final output that is wrapped or justified while
    still preserving the initial formatting of the lines.
    """
    self.leading = leading or ''
    self.hanging = hanging or ''
    self.length = length

  def __cmp__(self, other):
    if isinstance(other, Format) or \
       (hasattr(other, leading) and hasattr(other, hanging)):
      if self.leading == other.leading and self.hanging == other.hanging:
        return 0
      else:
        return -1
    else:
      return -1

class DummyRe:
  "Dummy regular expression class that defines a match() function that returns None"
  def match(self, pattern): pass

# performance optimization so we don't continually reinstantiante an empty Format object
FORMAT_BLANK = Format()

def wrap(string, length, formats=[FORMAT_BLANK], pdelims=[]):
  """
  Wrap the given string so that no single line is greater than length characters
  (unless it contains individual words that are longer than length, in which case
  the line will consist of just this word).  The string is split into paragraphs
  and each paragraph is processed separately.  wrap() attempts to match the Format
  objects specified in the formats argument against each paragraph; the first
  Format that matches will be the one used to perform the wrapping.  If no matching
  Format is found, raises a FormatMatchError.
  """
  # include the 'match all' format, if not present
  if FORMAT_BLANK not in formats: formats.append(FORMAT_BLANK)
  paras = []
  # split and process paragraphs separately
  for para in _split(string, pdelims):
    if DELIM_LINE.match(para):
      paras.append([para])
    else:
      paras.append(_wrap(para, length, pdelims+formats))
  return reformat(paras)

def _wrap(string, length, formats=[FORMAT_BLANK]):
  "wrap() helper function"
  # check each format sequentially, one at a time, until a match is found.
  # if no matches are found, raise a FormatMatchError
  for format in formats:
    try:
      leading = format.leading
      hanging = format.hanging
      ret = []
      # anchor regexps if not already anchored
      if format.leading is not None:
        if not format.leading.startswith('^'):
          format.leading = '^'+format.leading
        leadscan = re.compile(format.leading)
      else:
        leadscan = DummyRe()
      if format.hanging is not None:
        if not format.hanging.startswith('^'):
          format.hanging = '^'+format.hanging
        hangscan = re.compile(format.hanging)
      else:
        hangscan = DummyRe()

      # split string into lines
      lines = filter(lambda(x): not DELIM_LINE.match(x), DELIM_LINE.split(string))
      flsize = len(lines[0])
      # check first line to see if it matches the leading regex
      lmatch = leadscan.match(lines[0])
      if lmatch:
        leadprefix = lmatch.group()
        lines[0] = lines[0].replace(leadprefix, '', 1)
      elif format.leading is None:
        leadprefix = ''
      else:
        raise FormatMatchError, "First line '%s' does not match the specified lead prefix regex '%s'" % (lines[0], format.leading)

      # check remaining lines to see if they match the hanging regex
      hangprefix = ''
      for i in range(1, len(lines)):
        hmatch = hangscan.match(lines[i])
        if hmatch:
          if not hangprefix:
            hangprefix = hmatch.group()
          else:
            if not hangprefix == hmatch.group():
              raise FormatMatchError, "Hanging prefix '%s' does not match previous hanging prefix '%s'" % (hmatch.group(), hangprefix)
          lines[i] = lines[i].replace(hangprefix, '', 1)
        elif format.hanging is None:
          hangprefix = ''
        else:
          raise FormatMatchError, "Line %s does not match the specified hanging prefix regex '%s'" % (i, format.hanging)

      # tokenize input - don't justify lines that are 75% or less of the total width
      if (flsize*100)/(format.length or length) > 75:
        para = ' '.join(lines)
        tokens = _tokenize(para)
        lines = []
      else:
        firstline = lines.pop(0)
        para = ' '.join(lines)
        tokens = _tokenize(para)
        lines = [leadprefix+firstline]

      # construct lines of at most format.length chars, or if format.length
      # is not specified, length chars
      while len(tokens) > 0:
        if len(lines) == 0: # first line in the paragraph
          line = leadprefix
        else:
          line = hangprefix
        while len(tokens) > 0:
          if len(line) + len(tokens[0]) < (format.length or length):
            line += tokens.pop(0)
          else:
            if WHITESPACE.match(tokens[0]):
              tokens.pop(0) # don't process this whitespace, its redundant
            else:
              lines.append(line)
              line = hangprefix + tokens.pop(0)
              continue
            #  line += tokens.pop(0) # single token is longer than requested line
            break # start next line
        lines.append(line)
        line = hangprefix

      for i in range(0, len(lines)):
        lines[i] = lines[i].rstrip()
      return lines
    except FormatMatchError:
      pass # the current Format didn't match string, try next one

  # if we get this far, we haven't matched any formats
  raise ValueError, "Paragraph does not match any specified format"

def justify(string, length, formats=[FORMAT_BLANK], pdelims=[]):
  """
  Justify the input string, making it simultaneously left- and right-aligned.
  Lines will be created to be exactly length characters long; if a line is shorter
  than this size, it will be space-padded.  As with wrap(), above, if the input
  contains a word that is longer than length chars, it will be contained in a single
  line that is longer than length chars.  Paragraphs are processed separately, and
  each is matched against one of the Format objects specified in the formats
  argument.  The first matching Format is used; if no matches are found, raises a
  FormatMatchError.
  """
  # include the 'match all' format, if not present
  if FORMAT_BLANK not in formats: formats.append(FORMAT_BLANK)
  formats = pdelims + formats # try paragraph delimiters (list items) before formats
  paras = []
  # split and process paragraphs separately
  for para in _split(string, pdelims):
    if DELIM_LINE.match(para):
      paras.append([para])
    else:
      paras.append(_justify(para, length, formats))
  return reformat(paras)

def _justify(string, length, formats=[FORMAT_BLANK]):
  "justify() helper function"
  ret = []
  # wrap lines so they are at most length chars in length
  lines = _wrap(string, length, formats)

  # if lines is only 1 line long, no justification is necessary
  if len(lines) > 1:
    # perform formatting on the first line
    if len(lines[0]) < length:
      for format in formats:
        try:
          lines[0] = adjust(lines[0], format.length or length, format.leading)
          break
        except FormatMatchError:
          continue
        # if we get this far, the line matched none of the specified formats
        raise FormatMatchError, "Line %s does not match any of the specified formats" % 0
    else:
      raise ValueError, "DEBUG: First line too long"

    # perform formatting on 2nd through nth-1 line
    # last line does not need justification
    for i in range(1, len(lines)-1):
      if len(lines[i]) < length:
        for format in formats:
          try:
            lines[i] = adjust(lines[i], format.length or length, format.hanging)
            break
          except FormatMatchError:
            continue
          # if we get this far, the line matched none of the specified formats
          raise FormatMatchError, "Line %s does not match any of the specified formats" % i
      else:
        pass
  return lines

def adjust(string, length, lead=''):
  """Adjust the length of string so that it is exactly length chars long.  Checks
  to see if string matches the regex lead; if so, this section is not modified by
  adjust()."""
  if not lead.startswith('^'):
    lead = '^'+lead # anchor regex to beginning

  # determine if string starts with the lead regex
  scan = re.compile(lead)
  match = scan.match(string)
  if match:
    prefix = match.group()
  else:
    raise FormatMatchError, "Line does not match specified prefix"

  # remove the prefix
  #print 'PREFIX: "%s" LEAD: "%s"' % (prefix, lead)
  string = string.replace(prefix, '', 1)

  # tokenize string
  tokens = _tokenize(string)
  if len(tokens) < 2:
    return prefix + string

  # set up a list of the spaces; list contains the number of ' ' characters to use
  # this list is incremented later in order to perform the two-way justification
  spaces = {}
  for i in range(0, len(tokens)):
    t = tokens[i]
    if WHITESPACE.match(t):
      spaces[i] = len(t)
  indexes = spaces.keys()

  # figure out the current length before any padding is performed
  curlen = len(prefix)
  for token in tokens: curlen += len(token)
  if curlen > length:
    raise FormatMatchError, "DEBUG: Input string '%s' longer than specified length (%s > %s)" % (string, curlen, length)
    # this will eventually get fixed, perhaps

  # while curlen is less than length, insert spaces between random words.
  # a space can only be chosen once; if every space has been chosen once and
  # the string is still not long enough, another round of selection begins,
  # until the line becomes long enough
  if len(indexes) > 0:
    while curlen < length:
      # insert spaces until the line is the correct size
      index = _select(indexes)
      spaces[index] += 1
      tokens[index] += ' '
      curlen += 1
      indexes.remove(index)
      if len(indexes) == 0:
        indexes = spaces.keys()

  # construct final string
  retstr = prefix
  for i in range(0, len(tokens)):
    retstr += tokens[i]
  return retstr

def _select(list):
  "Select an element from list by some algorithm, currently random"
  return random.choice(list)

def reformat(paras):
  "Reconstruct a string from a list of paragraphs"
  # paragraphs consist of a list of lines, so first join the lines, then the
  # paragraphs
  lines = []
  for item in paras:
    lines.append('\n'.join(item))
  return ''.join(lines)

def _split(string, pdelims=[]):
  "Split a string into paragraphs; attempt to split on pdelims as well"
  ret = []

  dsleading = re.compile('([\s]*(?:\"\"\"|\'\'\'))\n')
  dstrailing = re.compile('\n([\s]*(?:\"\"\"|\'\'\'))')

  paras = filter(None, DELIM_PARA.split(string))
  for para in paras:
    if DELIM_PARA.match(para):
      ret.append(para)
      continue
    matched = False

    for delim in pdelims:
      if delim.leading.startswith('^'):
        lead = delim.leading.lstrip('^')
      else:
        lead = delim.leading
      leadscan = re.compile('(\n)(%s)' % lead)

      # split on leading indents
      plist = leadscan.split(para) # don't filter on purpose

      # split on docstring markers that occur on their own lines
      i = 0
      while i < len(plist):
        p = plist[i]
        split = filter(None, dsleading.split(p))
        if len(split) == 2:
          pre, p = split
          plist.insert(i, pre);  i += 1
          plist.insert(i, '\n'); i += 1
          plist[i] = p
        split = filter(None, dstrailing.split(p))
        if len(split) == 2:
          p, post = split
          plist[i] = p;          i += 1
          plist.insert(i, '\n'); i += 1
          plist.insert(i, post); i += 1
          plist.insert(i, '\n')
        i += 1

      # append paragraphs to return list
      if len(plist) > 0:
        ret.append(plist[0])
        matched = True
      if len(plist) > 1:
        ret.append(plist[1])
      if len(plist) > 2:
        i = 2
        while i < len(plist):
          if i + 2 <= len(plist)-1:
            ret.append(plist[i] + plist[i+1])
            ret.append(plist[i+2])
          elif i + 1 <= len(plist)-1:
            if plist[i+1] != '\n':
              ret.append(plist[i] + plist[i+1])
              ret.append('\n')
            else:
              ret.append(plist[i])
              ret.append(plist[i+1])
          else:
            #print plist
            #raise "DEBUG: malformed paragraphs?"
            ret.append(plist[i])
          i += 3

    if not matched: ret.append(para) # none of the specified bullets matched, just appent para

  # returns a list of strings, each a separate 'paragraph'
  return ret

def _tokenize(string):
  "Split a string into nonseperable words.  See TOKEN_SEP for behavior"
  return filter(None, TOKEN_SEP.split(string))

def _is_sentence_end(word):
  """Determine if a word is at the end of a sentence.  End of sentences are
  denoted by one of the characters ., !, or ?, optionally followed by
  either a ' or ".  There are a few limitations to this algorithm.  First, it
  incorrectly indicates 'Dr. Vaz' as being two sentences.  Second, the
  implementation is specific to the en_US locale."""
  if word[-1] in '"\'':
    if len(word) > 1 and word[-2] in '.?!': return True
  else:
    if word[-1] in '.?!': return True
  return False

class FormatMatchError(StandardError):
  "Class of error raised when an input string matches no Format objects"

if __name__ == '__main__':
  from openprovision.util import pps
  import sys

  if len(sys.argv) != 2:
    print 'usage: justify.py FILE'
    sys.exit(2)

  file = sys.argv[1]

  f = '\n'.join(pps.path(file).read_lines())
  print justify(f, 80, formats=[Format('^[\d]*\.[ ]*', '[ ]+', 76)])
  #print wrap(f, 80, formats=[Format('^[\d]*\.[ ]*', '[ ]+', 76)])
