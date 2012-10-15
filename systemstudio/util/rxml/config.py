#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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

Provides parse() and getxpath() functions, complete with fallback support.
"""

__author__   = 'Daniel Musgrave <dmusgrave@systemstudio.org>'
__version__  = '3.0'
__date__     = 'June 13th, 2007'

import lxml
import types

from xml.sax.saxutils import escape

from systemstudio.util import pps

from systemstudio.util.rxml import errors, tree

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
    # using getxpath('text()') below rather than self.text, as the latter returns
    # both text and tail. This matters, for example if the text contains 
    # a free floating element, e.g. a <!--comment-->.
    if self.getxpath('text()', None) is not None: text = escape(self.getxpath('text()'))
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

  def getxpath(self, paths, fallback=tree.NoneObject()):
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
      result = self.xpath(paths)[0]
      if isinstance(result, types.NoneType):
        return fallback
      else:
        return result
    except errors.XmlPathError:
      if not isinstance(fallback, tree.NoneObject):
        return fallback
      else:
        raise

  def xpath(self, paths, fallback=tree.NoneObject()):
    """
    Gets multiple values out of the configuration element

    Has the same API differences as getxpath(), above
    """
    if not hasattr(paths, '__iter__'): paths = [paths]
    result = []
    for p in paths:
      # special handling for text elements which can have multiple strings
      # in the text result (i.e. if there are comments in the string).
      # We first check if the xpath query results in multiple elements.  If so
      # we concat the text of each element before returning. If the xpath 
      # results in only a single element we likewise concat its results before
      # returning
      if '/text()' in p:
        base = p.replace('/text()', '')
        elems = tree.XmlTreeElement.xpath(self, base)
        if elems: 
          for elem in elems:
            subresult = elem.xpath('text()')
            if len(subresult) > 0:
              result.append(' '.join(subresult))
          if result: break
      elif 'text()' in p:
        result = tree.XmlTreeElement.xpath(self, p)
        if len(result) > 0:
          result = [ ' '.join(result) ]
        if result: break
      else:
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
    return _make_boolean(self.getxpath(path, fallback))

  def getpath(self, path, fallback=tree.NoneObject(), relative=False):
    return _make_path(self, path, fallback, relative=relative, multiple=False)

  def getpaths(self, path, fallback=tree.NoneObject(), relative=False):
    return _make_path(self, path, fallback, relative=relative, multiple=True)

  def pathexists(self, path):
    try:
      return self.getxpath(path) is not None
    except errors.XmlPathError:
      return False


class ConfigTreeSaxHandler(tree.XmlTreeSaxHandler):
  "SAX Content Handler."
  def __init__(self, makeelement=None):
    tree.XmlTreeSaxHandler.__init__(self, makeelement=makeelement)

  def endElementNS(self, ns_name, qname):
    element = self._element_stack.pop()
    if ns_name != lxml.sax._getNsTag(element.tag):
      raise lxml.sax.SaxError("Unexpected element closed: {%s}%s" % ns_name)

    # convert whitespace into None
    if element.getxpath('text()', None) is not None:
      element.text = element.getxpath('text()').strip() or None

#--------FACTORY FUNCTIONS--------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=True)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(element=ConfigElement,
                                                                  comment=tree.XmlTreeComment))

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

def parse(file, handler=None, parser=PARSER, **kwargs):
  config = tree.parse(file,
                     handler or ConfigTreeSaxHandler(parser.makeelement),
                     parser=parser,
                     **kwargs)
  return config

def fromstring(string, handler=None, parser=PARSER, **kwargs):
  return tree.fromstring(string,
                         handler=handler or ConfigTreeSaxHandler(parser.makeelement),
                         parser=parser,
                         **kwargs)

def _make_boolean(string):
  if isinstance(string, tree.XmlTreeElement):
    string = string.getxpath('text()')
  if not isinstance(string, (basestring, bool)):
    raise ValueError("query must return a string or boolean, got a %s" % type(string))
  try:
    if isinstance(string, basestring):
      return BOOLEANS[string.lower()]
    else:
      return BOOLEANS[string]
  except KeyError:
    raise ValueError("'%s' is not a valid boolean" % string)

def _make_path(element, path, fallback=None, relative=False, multiple=True):
  roottree = element.getroottree()

  # does the path query returns results?
  try:
    if path[0] != '/':
      path = '%s/%s' % (roottree.getpath(element), path)
    strings = roottree.xpath(path)
    test = strings[0] # trick to force an IndexError if list is empty

  # if not, set the fallback as the result
  except IndexError:
    strings = [ fallback ]
    # if fallback is a string, morph it to a pps path object 
    if isinstance(fallback, basestring):
      fallback = pps.path(fallback)

    return fallback
       
  # process results
  if not multiple: # filter to a single item if requested
    strings[:1]   
  for i in range(len(strings)):
    if not isinstance(strings[i], basestring):
      raise ValueError("query must return a string, got a %s" % 
                       type(strings[i]))

    # get the base for resolving relative paths
    ancestors = list(strings[i].getparent().iterancestors())
    ancestors.reverse()
    ancestors.append(strings[i].getparent())
    if isinstance(roottree.getroot().file, basestring) and not relative:
      base = pps.path(roottree.getroot().file).dirname
    else: # e.g. roottree could be a stringIO object rather than a file
      base = pps.path('.')
    for ancestor in ancestors:
      try:
        base = base / pps.path(ancestor.xpath("@xml:base")[0]).dirname
      except errors.XmlPathError:
        pass
    strings[i] = (base / strings[i]).normpath()

  if multiple: return strings
  else: return strings[0]
