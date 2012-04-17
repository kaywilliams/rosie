#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
import codecs
import lxml.etree
import lxml.sax
import re

from StringIO import StringIO

from centosstudio.util import pps

from centosstudio.util.rxml import errors

class NoneObject: pass

class XmlTreeObject(object):
  def __str__(self):
    return self.tostring().encode('ascii', 'replace')

  def unicode(self):
    return unicode(self.tostring())

  def tostring(self, lineno=False):
    s = self._tostring()
    if lineno:
      srcline = self.sourceline or 0
      pad = len(str(getattr(self.getroot(), 'maxlineno', 0)))
      rtn = ''
      for i, item in enumerate(s.split('\n')):
        # looks like ' 45:<some-xml-line/>'
        rtn += '%%s%%%dd:%%s' % pad % (i != 0 and '\n' or '', srcline+i, item)
      return rtn
    else:
      return s

  def _tostring(self):
    string = lxml.etree.tostring(self)
    for k,v in self.nsmap.items():
      string = string.replace('%s:' % k, '').replace(':%s' % k, '')
    return string

  def getroot(self):
    return self.getroottree().getroot()

class XmlTreeComment(lxml.etree.CommentBase, XmlTreeObject):
  pass

class XmlTreeElement(lxml.etree.ElementBase, XmlTreeObject):
  """
  XmlTreeElements are data structures designed to represent XML
  elements in memory in a DOM (Document-Object Model) style.  As such,
  they contain a tag attribute for the element tag, a text attribute
  for the text of the XML element, and an attrs attribute for XML
  attributes.  Furthermore, XmlTreeElements contain a list of all
  child nodes, as well as pointers to parent, first/last children, and
  previous/next sibling.

  Implements most of the functions required to act as a list.  Thus,
  XmlTreeElements can be indexed using [...] and modified using
  standard list functions.  Slicing is not currently supported, though
  it could most likely be added relatively easily.  Additionally,
  certain list functions like sort() and reverse() are not supported
  because they don't really make sense in an XML document.  These
  functions all take into account the special structure of
  XmlTreeElements; so, for example, append() adds an element to the
  parent's children list and correctly updates parent.lastchild as
  well as the old parent.lastchild's nextsibling and the elements
  prevsibling fields.
  """
  def __eq__(self, other):
    if not isinstance(other, XmlTreeElement): return False
    if self.tag != other.tag: return False
    if (self.text or '').strip() != (other.text or '').strip(): return False
    if len(self.attrib) != len(other.attrib): return False
    for k,v in self.attrib.items():
      if other.attrib.has_key(k):
        if other.attrib[k] != v: return False
      else:
        return False
    myc = self.getchildren()
    oc  = other.getchildren()
    if len(myc) != len(oc): return False
    for i in range(0, len(myc)):
      if myc[i] != oc[i]: return False
    return True

  def __ne__(self, other):
    return not self.__eq__(other)

  def getxpath(self, path, fallback=NoneObject(), namespaces=None, extensions=None):
    """
    Get one or more nodes out of the XML tree.

    A node can be an element, attribute, or text node.

    path should be a valid XPath expression.
    """
    result = self.xpath(path, namespaces=namespaces, extensions=extensions)
    if len(result) == 0:
      if not isinstance(fallback, NoneObject):
        return fallback
      else:
        return None
    else:
      return result[0]

  def xpath(self, path, fallback=NoneObject(), namespaces=None, extensions=None):
    if not namespaces:     namespaces = self.getroot().nsmap
    if None in namespaces: namespaces.pop(None) # None in namespaces raises an exception
    try:
      result = lxml.etree.ElementBase.xpath(self, path,
                                            namespaces=namespaces,
                                            extensions=extensions)
      if len(result) == 0 and not isinstance(fallback, NoneObject):
        return fallback
      else:
        rtn = []
        for item in result:
          if isinstance(item, str):
            rtn.append(item.strip())
          else:
            rtn.append(item)
        return rtn
    except lxml.etree.XPathSyntaxError:
      raise errors.XmlPathError("syntax error in path expression '%s'" % path)

  def getchildren(self, elemonly=True):
    children = lxml.etree.ElementBase.getchildren(self)
    if elemonly:
      children = [ x for x in children if isinstance(x, XmlTreeElement) ]
    return children

  def pathexists(self, path):
    return self.getxpath(path) is not None

  def get_or_create(self, child):
    """
    Gets the node, per getxpath(), or, if it doesn't exist, attempts to
    create it.  Only works on one level (that is, only on this node's
    direct descendants.
    """
    if not self.haschild(child): # create
      return Element(child, parent=self)
    else:
      self.getxpath(child)

  def haschild(self, child):
    return len(self.xpath(child, [])) > 0

  def replace(self, map):
    "performs string replacement across all attributes and text elements"
    for key in map:
      for elem in self.iter():
        for attr in elem.attrib.keys():
          if key in elem.attrib[attr]:
            elem.attrib[attr] = elem.attrib[attr].replace(key, map[key])
        if elem.text is not None:
          if key in elem.text:
            elem.text = elem.text.replace(key, map[key])
        if elem.tail is not None:
          if key in elem.tail:
            elem.tail = elem.tail.replace(key, map[key])

  def resolve_macros(self, xpaths=None, map=None):
    """
    Processes macro elements (reads and removes) and resolves macro variables.
    Macro elements take the format '<macro id='name'>value</macro>'. They can
    be defined at any level of the element. Macro variables use the syntax
    '%{name}'. Macro variables can occur in element nodes and attributes.

    Keyword arguments: 
    xpaths -- a list of xpath queries to be searched for macros. The
    provided queries must return element nodes. The default value is '['/*']',
    meaning that resolve_macros will search for macros only at the top-level
    of the element. To search for macros at any level, provide a dot character 
    in the xpath string, e.g. ['.'].
    
    map -- a dictionary containing existing macro definitions to use in
    addition to any discovered macros, e.g.

        map = {'%{name1}: 'value1'
                %{name2}: 'value2'}
    """
    xpaths = xpaths or ['/*']
    map = map or {}

    # locate and remove macro definitions
    for item in xpaths:
      if item == '.':
        item = '/'
      for elem in self.xpath('%s/macro' % item, []):

        try:
          name = '%%{%s}' % elem.attrib['id']
        except KeyError:
          message = "Missing required 'id' attribute." 
          raise errors.MacroError(self.getroot().file, message, elem)

        if name not in map: # use outermost macro definition
          value = elem.getxpath('node()', '')
          if not isinstance(value, basestring):
            message = ("Macro content must be text. See the documentation for "
                       "information on using 'xml' elements and xinclude "
                       "for including xml content.")
            raise errors.MacroError(self.getroot().file, message, elem)
          map[name] = value

        elem.getparent().remove(elem)

    # resolve macros in map - recursive
    p = re.compile('%{[^}]*}')
    for macro in map:
      unknown = set() # ignore unknown macros, perhaps they aren't really macros
      resolved = False
      while resolved == False: # loop until all macros are resolved or unknown
        remaining = set(p.findall(map[macro])).difference(unknown)
        if remaining: 
          for match in remaining:
            if match in map.keys():
              map[macro] = map[macro].replace(match, map[match])
            else:
              unknown.add(match)
        else: 
          resolved = True

    # check for circular references
    for key in map:
      if key in map[key]:
        message = ("Macro Resolution Error: The macro value '%s' contains "
                   "a circular reference to the macro name '%s'." % 
                   (map[key], key))
        raise errors.XmlError(message)

    # expand macros
    for item in xpaths:
      for elem in self.xpath(item.rstrip('/'), []):
        elem.replace(map)

  def write(self, file):
    file = pps.path(file)
    if not file.exists: file.mknod()

    f = codecs.open(file, encoding='utf-8', mode='w')
    f.write(self.unicode())
 
#-----------SAX-----------#
class XmlTreeSaxHandler(lxml.sax.ElementTreeContentHandler):
  def __init__(self, makeelement=None):
    lxml.sax.ElementTreeContentHandler.__init__(self, makeelement=makeelement)

    self._ns_mapping = {'xml': ['http://www.w3.org/XML/1998/namespace'] }
    self.lineno = 1

  def startElementNS(self, *args, **kwargs):
    lxml.sax.ElementTreeContentHandler.startElementNS(self, *args, **kwargs)
    self._element_stack[-1].sourceline = self.lineno

  def characters(self, data):
    lxml.sax.ElementTreeContentHandler.characters(self, data)
    self.lineno += data.count('\n')

  def comment(self, data):
    c = lxml.etree.Comment(data)
    if self._root is None:
      self._root_siblings.append(c)
    else:
      self._element_stack[-1].append(c)
    c.sourceline = self.lineno

class XmlTreeProducer(lxml.sax.ElementTreeProducer):
  def __init__(self, eot, handler):
    lxml.sax.ElementTreeProducer.__init__(self, eot, handler)
    handler.lineno = self._element.sourceline

  def _recursive_saxify(self, element, prefixes):
    content_handler = self._content_handler
    tag = element.tag
    if tag is lxml.etree.Comment or tag is lxml.etree.ProcessingInstruction:
      if tag is lxml.etree.ProcessingInstruction:
        content_handler.processingInstruction(
          element.target, element.text
        )
      if tag is lxml.etree.Comment:
        content_handler.comment(element.text)
      if element.tail:
        content_handler.characters(element.tail)
      return

    new_prefixes = []
    build_qname = self._build_qname
    element_prefix = element.prefix

    attribs = element.items()
    if attribs:
      attr_values = {}
      attr_qnames = {}
      for attr_ns_name, value in attribs:
        attr_ns_tuple = lxml.sax._getNsTag(attr_ns_name)
        attr_values[attr_ns_tuple] = value
        attr_qnames[attr_ns_tuple] = build_qname(
          attr_ns_tuple[0], attr_ns_tuple[1], prefixes, new_prefixes, element_prefix)
      sax_attributes = self._attr_class(attr_values, attr_qnames)
    else:
      sax_attributes = self._empty_attributes

    ns_uri, local_name = lxml.sax._getNsTag(tag)

    qname = build_qname(ns_uri, local_name, prefixes, new_prefixes, element_prefix)

    for prefix, uri in new_prefixes:
      content_handler.startPrefixMapping(prefix, uri)

    content_handler.startElementNS((ns_uri, local_name),
                     qname, sax_attributes)
    if element.text is not None:
      content_handler.characters(element.text)
    for child in element:
      self._recursive_saxify(child, prefixes)
    content_handler.endElementNS((ns_uri, local_name), qname)
    for prefix, uri in new_prefixes:
      content_handler.endPrefixMapping(prefix)
    if element.tail:
      content_handler.characters(element.tail)

  def _build_qname(self, ns_uri, local_name, prefixes, new_prefixes, element_prefix):
    if ns_uri is None:
      return local_name
    try:
      prefix = prefixes[ns_uri]
    except KeyError:
      prefix = prefixes[ns_uri] = element_prefix or 'ns%02d' % len(new_prefixes)
      new_prefixes.append( (prefix, ns_uri) )
    return prefix + ':' + local_name

#-----------FACTORY FUNCTIONS-----------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=False)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(element=XmlTreeElement,
                                                                  comment=XmlTreeComment))

def saxify(tree, handler):
  return XmlTreeProducer(tree, handler).saxify()

# TODO - perhaps have Element accept *args, **kwargs instead
def Element(name, parent=None, text=None, attrs=None, nsmap=None, parser=PARSER):
  if nsmap is None and hasattr(parent, 'nsmap'):
    nsmap = parent.nsmap
  elem = parser.makeelement(name, attrib=attrs or {}, nsmap=nsmap)
  elem.text = text or ''
  if parent is not None:
    parent.append(elem)
  return elem

def uElement(name, parent, attrs=None, text=None, **kwargs):
  # the below is more elegant, but won't work because Elements subclass
  # list, and lists evaluate to false when empty
  #
  # return parent.getxpath(name, None) or Element(name, parent=parent, **kwargs)
  elem = parent.getxpath(name, None)
  if elem is None:
    elem = Element(name, parent=parent, attrs=attrs, text=text, **kwargs)
  else:
    if text is not None:
      elem.text = text
    if attrs:
      for k,v in attrs.items():
        if v:
          elem.attrib[k] = v
        else:
          del(elem.attrib[k])
  return elem

def parse(file, handler=None, parser=PARSER, macro_xpaths=None, macro_map=None):
  handler = handler or XmlTreeSaxHandler(parser.makeelement)
  try:
    roottree = lxml.etree.parse(file, parser)
  except lxml.etree.XMLSyntaxError, e:
    raise errors.XmlSyntaxError(file, e)

  roottree.getroot().file = file # set this now so the filename can be used in
                                 # macro error text
  
  count = 0
  while count <= 1:
    roottree.getroot().resolve_macros(macro_xpaths, macro_map)
    try:
      roottree.xinclude()
    except lxml.etree.XIncludeError, e:
      if count == 0: # try again after resolving macros (again)
        count += 1
      else: # resolving macros didn't help, so raise an error 
        raise errors.XIncludeSyntaxError(file, e)
    else:
      if (roottree.find('.//{http://www.w3.org/2001/XInclude}include') 
          is not None):
        count += 1 # no errors, but still unresolved xincludes...
      else:
        break # no errors, no unresolved xincludes, we're good to go

  # resolve macros a final time, removing macro definitions, once the xinclude
  # proces is complete
  roottree.getroot().resolve_macros(macro_xpaths, macro_map)

  saxify(roottree, handler)
  handler._root.file = file
  handler._root.maxlineno = handler.lineno
  return handler.etree

def fromstring(s, **kwargs):
  root = parse(StringIO(s), **kwargs).getroot()
  root.file = None
  return root
