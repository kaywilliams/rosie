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
A configuration reading library.

Provides read() and get() functions, complete with fallback support.
"""

__author__   = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__  = '3.0'
__date__     = 'June 13th, 2007'

import lxml

from xml.sax.saxutils import escape

from solutionstudio.util import pps

from solutionstudio.util.rxml import errors, tree

BOOLEANS = {
  # True equivalents
  'true':  True,
  'yes':   True,
  'on':    True,
  '1':     True,
  True:    True,
  # False equivalents
  'false': False,
  'no':    False,
  'off':   False,
  '0':     False,
  False:   False,
}

# this isn't portable to non-ANSI terminals; we don't care right now
ANSI_HIGHLIGHT_START = '\033[1m'
ANSI_HIGHLIGHT_END   = '\033[0;0m'
ANSI_HIGHLIGHT = '%s%%s%s' % (ANSI_HIGHLIGHT_START, ANSI_HIGHLIGHT_END)

HIGHLIGHT_ATTRS = 0001
HIGHLIGHT_NODES = 0010
HIGHLIGHT_TEXT  = 0100

#-------- CLASSES --------#
class ConfigElement(tree.XmlTreeElement):
  "An element in the XML tree."

  def tostring(self, xpath=None):
    nodes = []
    highlight = 0000
    if xpath:
      try:
        root, base = xpath.rsplit('/', 1)
      except ValueError:
        root, base = '.', xpath
      if root.endswith('/'): # xpath was root//base, not root/base
        root += '/*' # transform xpath into root//* (select all children)
      if base == 'text()': # text
        highlight = HIGHLIGHT_TEXT
        nodes = self.getroot().xpath(root, [])
      elif base.startswith('@'): # attribute
        highlight = HIGHLIGHT_ATTRS
        nodes = self.getroot().xpath(root, [])
      else: # normal nodes
        highlight = HIGHLIGHT_NODES
        nodes = self.getroot().xpath(xpath, [])

    return self._tostring(0, nodes, highlight)

  def _tostring(self, level=0, nodes=None, highlight=None):
    tag = ''; text = ''; data = ''; attr = ''

    enable_hl = self in (nodes or [])
    do_node_hl = enable_hl and highlight & HIGHLIGHT_NODES
    do_attr_hl = enable_hl and highlight & HIGHLIGHT_ATTRS
    do_text_hl = enable_hl and highlight & HIGHLIGHT_TEXT

    # separator
    sep = '  ' * level
    if do_node_hl: sep = ANSI_HIGHLIGHT_START + sep

    # newline
    if self == self.getroot(): nl = ''
    else: nl = '\n'
    if do_node_hl: nl = nl + ANSI_HIGHLIGHT_END

    # tag
    tag = self._ns_clean(self.tag)

    # text
    if self.text is not None: text = escape(self.text)
    if do_text_hl: text = ANSI_HIGHLIGHT % text

    # attributes
    for k,v in self.attrib.items():
      attrtxt = ' %s="%s"' % (self._ns_clean(k), escape(v))
      ##if do_attr_hl and k in highlight_xpath_attrs or []:
      if do_attr_hl: #!
        attr += ANSI_HIGHLIGHT % attrtxt
      else:
        attr += attrtxt

    # children
    for i in self.getchildren():
      data += i._tostring(level+1, nodes, highlight)

    if len(data) > 0:
      return unicode('%s<%s%s>%s\n%s%s</%s>%s' % \
                     (sep, tag, attr, text, data, sep, tag, nl))
    elif len(text) > 0:
      return unicode('%s<%s%s>%s</%s>%s' % \
                     (sep, tag, attr, text, tag, nl))
    else:
      return unicode('%s<%s%s/>%s' % (sep, tag, attr, nl))

  def _ns_clean(self, text):
    uri, name = lxml.sax._getNsTag(text)
    if uri:
      # lxml deletes xml definition from the nsmap
      if uri == 'http://www.w3.org/XML/1998/namespace':
        return 'xml:%s' % name
      else:
        for k,v in self.nsmap.items():
          if v == uri:
            return '%s:%s' % (k, name)
      raise ValueError("No matching prefix found for namespace '%s'" % uri)
    return name

  def get(self, paths, fallback=tree.NoneObject()):
    """
    Generic get method for data stored within a configuration element.

    Has the same API and behavior as xml.tree except for the
    following:
     * accepts a list of paths instead of a single path.  The first
       path to match something in the config file is the one used for
       returning
     * if no matches are found and no fallback is specified, raises an
       XmlPathError
     * attempting to match a text() node that contains no non-whitespace
       characters will result in returning None rather than the whitespace
       characters themselves
    """
    try:
      return self.xpath(paths)[0]
    except errors.XmlPathError:
      if not isinstance(fallback, tree.NoneObject):
        return fallback
      else:
        raise

  def xpath(self, paths, fallback=tree.NoneObject()):
    """
    Gets multiple values out of the configuration element

    Has the same API differences as get(), above
    """
    if not hasattr(paths, '__iter__'): paths = [paths]
    result = []
    for p in paths:
      result = tree.XmlTreeElement.xpath(self, p)
      if result: break

    if len(result) == 0:
      if not isinstance(fallback, tree.NoneObject):
        return fallback
      else:
        raise errors.XmlPathError("None of the specified paths %s "
                                  "were found in the config file" % paths)

    # convert empty/whitespace-only strings to None before returning
    for i in range(0, len(result)):
      if isinstance(result[i], basestring):
        if not result[i].strip():
          result[i] = None

    return result

  def getbool(self, path, fallback=tree.NoneObject()):
    return _make_boolean(self.get(path, fallback))

  def getpath(self, path, fallback=tree.NoneObject()):
    return _make_path(self.get(path, fallback), fallback)

  def getpaths(self, path, fallback=tree.NoneObject()):
    return [ _make_path(x) for x in self.xpath(path, fallback) ]

  def pathexists(self, path):
    try:
      return self.get(path) is not None
    except errors.XmlPathError:
      return False


#--------FACTORY FUNCTIONS--------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=True)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(element=ConfigElement,
                                                                  comment=tree.XmlTreeComment))

def saxify(t):
  def convert_text(elem):
    # convert text consisting of just whitespace into None
    if elem.text is not None:
      elem.text = elem.text.strip() or None
  def strip_ns(elem):
    # completely remove namespaces
    if not isinstance(elem, tree.XmlTreeComment): # don't do comments
      i = elem.tag.find('}')
      if i > 0:
        elem.tag = elem.tag[i+1:]

  tree.saxify(t)
  root = t.getroot()

  strip_ns(root)
  convert_text(root)
  for elem in root.iterdescendants():
    strip_ns(elem)
    convert_text(elem)

def Element(name, parent=None, text=None, attrs=None, parser=PARSER, **kwargs):
  t = tree.Element(name, parent=parent, text=text, attrs=attrs,
                         parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def uElement(name, parent, text=None, attrs=None, parser=PARSER, **kwargs):
  t =  tree.uElement(name, parent=parent, text=text, attrs=attrs,
                           parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def read(file, saxifier=saxify, parser=PARSER):
  config = tree.read(file, saxifier=saxifier, parser=parser)
  config.file = file
  return config

def fromstring(string, saxifier=saxify, parser=PARSER, **kwargs):
  return tree.fromstring(string,
                         saxifier=saxifier,
                         parser=parser,
                         **kwargs)

def _make_boolean(string):
  if isinstance(string, tree.XmlTreeElement):
    string = string.text
  if not isinstance(string, (basestring, bool)):
    raise ValueError("query must return a string or boolean, got a %s" % type(string))
  try:
    if isinstance(string, basestring):
      return BOOLEANS[string.lower()]
    else:
      return BOOLEANS[string]
  except KeyError:
    raise ValueError("'%s' is not a valid boolean" % string)

def _make_path(string, fallback=None):
  if isinstance(string, tree.XmlTreeElement):
    string = string.text
  elif string is None:
    string = fallback
  if string is None:
    return fallback
  if not isinstance(string, basestring):
    raise ValueError("query must return a string, got a %s" % type(string))

  return pps.path(string)
