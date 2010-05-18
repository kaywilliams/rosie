#
# Copyright (c) 2007, 2008
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
import codecs
import lxml.etree
import lxml.sax

from StringIO import StringIO

from solutionstudio.util import pps

from solutionstudio.util.rxml import errors

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
    return lxml.etree.tostring(self)

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

  def get(self, path, fallback=NoneObject(), namespaces=None, extensions=None):
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
    return self.get(path) is not None

  def get_or_create(self, child):
    """
    Gets the node, per get(), or, if it doesn't exist, attempts to
    create it.  Only works on one level (that is, only on this node's
    direct descendants.
    """
    if not self.haschild(child): # create
      return Element(child, parent=self)
    else:
      self.get(child)

  def haschild(self, child):
    return len(self.xpath(child, [])) > 0

  def write(self, file):
    file = pps.path(file)
    if not file.exists: file.mknod()

    f = codecs.open(file, encoding='utf-8', mode='w')
    f.write(self.unicode())

#-----------FACTORY FUNCTIONS-----------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=False)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(element=XmlTreeElement,
                                                                  comment=XmlTreeComment))

def saxify(tree):
  # update line numbers after xincluding is complete
  root = tree.getroot()
  root.sourceline = 1
  lineno = 1 + ((root.text or '') + (root.tail or '')).count('\n')
  for elem in root.iterdescendants():
    elem.sourceline = lineno
    lineno += ((elem.text or '') + (elem.tail or '')).count('\n')

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
  # return parent.get(name, None) or Element(name, parent=parent, **kwargs)
  elem = parent.get(name, None)
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

def read(file, saxifier=None, parser=PARSER):
  saxifier = saxifier or saxify
  try:
    roottree = lxml.etree.parse(file, parser)
  except lxml.etree.XMLSyntaxError, e:
    print pps.path(file).read_text()
    raise errors.XmlSyntaxError(file, e)
  else:
    try:
      roottree.xinclude()
    except lxml.etree.XIncludeError, e:
      print pps.path(file).read_text()
      raise errors.XIncludeSyntaxError(file, e)

  saxifier(roottree)
  roottree.getroot().file = file
  return roottree.getroot()

def fromstring(s, **kwargs):
  root = read(StringIO(s), **kwargs)
  root.file = None
  return root
