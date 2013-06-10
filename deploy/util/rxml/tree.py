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
import codecs
import re

from copy import deepcopy
from StringIO import StringIO

from lxml import etree, sax

from deploy.util import pps

from deploy.util.rxml import errors

XI_NS = "http://www.w3.org/2001/XInclude"
XML_NS = "http://www.w3.org/XML/1998/namespace"
RE_NS = "http://exslt.org/regular-expressions"
MACRO_REGEX = '%{(?:(?!%{).)*?}' # match inner macros (e.g. '%{version}' in 
                                 # '%{packages-%{version}}'

class NoneObject: pass

class XmlTreeObject(object):
  def __str__(self):
    return self.tostring().encode('ascii', 'replace')

  def unicode(self):
    return unicode(self.tostring())

  def tostring(self, lineno=False, **kwargs):
    s = XmlTreeObject._tostring(self, **kwargs)
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

  def _tostring(self, **kwargs):
    string = etree.tostring(self, **kwargs)
    for k,v in self.nsmap.items():
      if v == XML_NS: # use consistent 'xml' prefix for xml namespace
        string = string.replace('xmlns:%s' % k, 'xmlns:xml')
      elif v == XI_NS: # strip xinclude namespace
        string = string.replace('xmlns:%s="%s" ' % (k, v), '')
      else: # used for repomd files - todo handle using custom elem class  
        string = string.replace('%s:' % k, '').replace(':%s' % k, '')
    return string

  def getroot(self):
    return self.getroottree().getroot()

class XmlTreeComment(etree.CommentBase, XmlTreeObject):
  pass

class XmlTreeElement(etree.ElementBase, XmlTreeObject):
  """
  XmlTreeElements are data structures designed to represent XML
  elements in memory in a DOM (Document-Object Model) style.  As such,
  they contain a tag attribute for the element tag, a text attribute
  for the text of the XML element, and an attrib attribute for XML
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
    if (self.tail or '').strip() != (other.tail or '').strip(): return False
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

  def addprevious(self, elem):
    "preserve base during element move"
    base = elem.base
    etree.ElementBase.addprevious(self, elem)
    if base != self.base:
      elem.base = base  

  def copy(self):
    "return a copy of the element, preserving the base"
    new = deepcopy(self)
    if self.base:
      new.base = self.base

    return new

  def getbase(self):
    return pps.path(self.base)

  def updatebase(self, parent, child):
    """
    Updates the base attribute of a child element. The new base is calculated
    relative to the parent.
    """
    oldbase = pps.path(child.getbase())
    newbase = oldbase.relpathfrom(parent.getbase())

    if not newbase:
      return

    if newbase == '.':
      if '{%s}base' % XML_NS in child.attrib:
        del child.attrib['{%s}base' % XML_NS]
      else:
        return

    else:
      child.attrib['{%s}base' % XML_NS] = newbase
    
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
      result = etree.ElementBase.xpath(self, path,
                                            namespaces=namespaces,
                                            extensions=extensions)
      if len(result) == 0 and not isinstance(fallback, NoneObject):
        return fallback
      else:
        #if len(result) == 1 and isinstance(result, basestring):
        #  result = result
        rtn = []
        for item in result:
          if isinstance(item, basestring):
            if not (item.is_tail and item.getparent() != self):
              rtn.append(item.strip())
          else:
            rtn.append(item)
        return rtn
    except etree.XPathSyntaxError:
      raise errors.XmlPathError("syntax error in path expression '%s'" % path)

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

  def remove(self, elem):
    if not elem.tail or not elem.tail.strip():
      etree.ElementBase.remove(self, elem)

    else:
      previous = elem.getprevious()

      # add tail to previous elem tail
      if previous is not None:
        previous.tail = (previous.tail or '') + elem.tail
        etree.ElementBase.remove(self, elem)

      # add tail to self text
      else:
        self.text = (self.text or '') + elem.tail
        etree.ElementBase.remove(self, elem)

  def replace(self, child, value):
    """
    Replace child element with value. Value accepts text, an element, or a list
    of text and elements
    """
    if isinstance(value, basestring) or isinstance(value, etree._Element):
      value = [value]

    for v in value:
      if isinstance(v, basestring):
        if not v.strip(): 
          continue # ignore whitespace only items
        if (isinstance(v, etree._ElementStringResult) and 
            v.is_tail and v.getparent() in value):
          continue # ignore tails
        self.text = (self.text or '') + v
      else:
        if isinstance(v, etree.ElementBase):
          child.addprevious(v)

    self.remove(child)

  def resolve_macros(self, find=False, map={}, placeholder_xpath='.'):
    """
    Processes macro definitions and resolves macro variables.  Macro
    definitions take the format '<macro id='name'>value</macro>'. They can
    exist at any level of the element. Macro variables use the syntax
    '%{macroid}'. Macro variables can occur in element nodes and attributes.

    Keyword arguments:
    find -- a boolean value indicating whether macro definitions should be
    discovered  and removed from the element and its descendants.  The default
    value is False.
    
    map -- a dictionary containing existing macro definitions to use in
    addition to any found macros, e.g.

        map = {'%{name1}: 'value1'
                %{name2}: 'value2'}

    Provided macros take precedence over found macros.

    placeholder_xpath -- query providing path to the root element to
    be searched for macro placeholders. If not provided, the current
    element will be searched. If the xpath does not return an element,
    resolve macros will return silently.

    Macro definitions are always searched from the root of the 
    current element.

    Returns a dictionary of provided and found macros.

    """
    search_elem = etree.ElementBase.xpath(self, placeholder_xpath)
    if len(search_elem) == 0:
      return
    else:
      search_elem = search_elem[0]

    map = map or {}

    # locate and remove macro definitions
    if find:
      for elem in self.xpath('//macro', []): 
        # ignore parent macro (until later loops)
        if [ x for x in elem.iterchildren('macro') ]:
          continue

        # validate element
        if not 'id' in elem.attrib:
          message = "Missing required 'id' attribute."
          raise errors.MacroError(self.getroot().base, message, elem)
  
        if re.findall(MACRO_REGEX, elem.attrib['id']):
          message = "Macros not allowed in macro ids."
          raise errors.MacroError(self.getroot().base, message, elem)
  
        # add elem content to map
        name = '%%{%s}' % elem.attrib['id']
        if name not in map: # higher level macros trump lower ones
          if len(elem) > 0:
            value = elem # add the element as the value
          elif elem.text:
            value = elem.text
          else:
            value = ''

          # check for circular references
          if name in value:
            message = ("Macro value contains a circular reference to "
                       "the macro id.")
            raise errors.MacroError(self.getroot().base, message, elem)
  
          # add elem value to macros
          map[name] = value 
 
    if not map: # no macros to resolve
      return

    # resolve macros
    unknown = set() # macro references with no corresponding definition

    while True:
      remaining = set(re.findall(MACRO_REGEX,
                  etree.tostring(search_elem))).difference(unknown)

      if not remaining:
        break

      for macro in remaining:
        # ignore unknown
        if not macro in map:
          unknown.add(macro)
          continue

        # text and tails
        strings = etree.ElementBase.xpath(search_elem,
                  ".//text()[re:test(., '.*%s.*', 'g')]" % macro,
                  namespaces={'re':RE_NS})

        for string in strings:
          parent = string.getparent()

          if isinstance(map[macro], basestring): # macro is string
            if string.is_text:
              parent.text = string.replace(macro, map[macro])
            if string.is_tail:
              parent.tail = string.replace(macro, map[macro])

          else: # macro is macro element
            text, tail = string.split(macro, 1)
            elems = [ x.copy() for x in map[macro] ]
            elems.reverse()

            if string.is_text:
              parent.text = text + (map[macro].text or '')
              for elem in elems:
                parent.insert(0, elem)
              elems[0].tail = (elems[0].tail or '') + tail 

            if string.is_tail:
              grandparent = parent.getparent()
              parent.tail = text + (map[macro].text or '')
              for elem in elems:
                grandparent.insert(grandparent.index(parent) + 1, elem)
              elems[0].tail = (elems[0].tail or '') + tail

        # attributes
        attribs = [ x for x in etree.ElementBase.xpath(search_elem, './/@*') 
                    if macro in x ]

        for attrib in attribs:
          if not isinstance(map[macro], basestring):
            message = ("Element content not allowed in attribute values.\n\n"
                       "The macro is defined as:\n" 
                       "%s\n\n" % map[macro].tostring(lineno=True,
                       with_tail=False))
            raise errors.MacroError(self.getroot().base, message,
                                    attrib.getparent())
          parent = attrib.getparent()
          for key, value in parent.attrib.items():
            parent.attrib[key] = value.replace(macro, map[macro])

    return map

  def remove_macros(self):
    for elem in self.xpath('.//macro', []):
      elem.getparent().remove(elem)

  def write(self, file):
    file = pps.path(file)
    if not file.exists: file.mknod()

    f = codecs.open(file, encoding='utf-8', mode='w')
    f.write(self.unicode())
 
  def xinclude(self, macros={}):
    """
    XInclude processor with integrated support for macro resolution
    """

    hrefs = {} # cache of previously included files

    # resolve macros
    macros = self.resolve_macros(find=True, map=macros) 

    while True:
      elems = self.xpath('//xi:include', [], namespaces=({'xi': XI_NS}))

      if not elems: 
        break

      # process xincludes
      for elem in elems:
        if elem.getparent() is None: parent = self
        else: parent = elem.getparent()
        if elem.tag == "{%s}include" % XI_NS:

          # validate
          if not 'href' in elem.attrib and not 'xpointer' in elem.attrib:
            raise errors.XIncludeError(message='Element must include at least '
                                       'one href or xpointer attribute',
                                       elem=elem)

          for key in elem.attrib:
            if key not in ['href', 'xpointer', 'parse', '{%s}base' % XML_NS ]:
              raise errors.XIncludeError(message="Unknown or unsupported "
                                         "attribute '%s'" % key, elem=elem)


          # process local includes
          if 'xpointer' in elem.attrib and not 'href' in elem.attrib:
            self._process_xpointer(source=self, parent=parent, target=elem)
            continue

          # process remote includes
          if 'href' in elem.attrib:
           # get absolute href
            base = pps.path(elem.base or '.')
            href = (base.dirname / elem.attrib['href']).normpath()

            # text
            if 'parse' in elem.attrib and elem.attrib['parse'] == 'text':
              if href in hrefs: # use cached text if available
                text = hrefs[href]
              else:
                try:
                  text = href.read_text()
                except (pps.Path.error.PathError), e:
                  raise errors.XIncludeError(e, elem)
              hrefs[href] = text # cache for future use

              parent.replace(elem, text)

            # xml
            else:
              if href in hrefs: # use cached document if available
                root = hrefs[href]
              else:
                try:
                  root = parse(href, parser=elem.getroottree().parser,
                               xinclude=True,
                               macros = macros,
                               base_url=href).getroot()
                except (IOError), e:
                  raise errors.XIncludeError(e, elem)
              hrefs[href] = root # cache for future use

              if 'xpointer' in elem.attrib:
                self._process_xpointer(source=root, parent=parent, target=elem)
              else: # insert entire xml document
                elem.addprevious(root.copy())

                parent.remove(elem)

  def _process_xpointer(self, source, parent, target):
    source = source.copy()
    xpath = re.sub(r'xpointer\((.*)\)$', r'\1', target.attrib['xpointer'])
    try:
      results = etree.ElementBase.xpath(source, xpath)
      if not hasattr(results, '__iter__'): # xpath can return bool and numeric
                                           # values, e.g
                                           # xpointer(./repo/@id='epel') returns
                                           # bool. s/b (./repo[@id='epel']) 
        raise errors.XIncludeError(message='Xpointer does not return text or '
                                           'XML content',
                                   elem=target)
      list = [ x for x in results
               if isinstance(x, etree._Element) or
                 (isinstance(x, basestring) and x.strip()) ]
    except etree.XPathError, e:
      raise errors.XIncludeXpathError(message=e, elem=target)

    if not list:
      raise errors.XIncludeError(message='No results found', elem=target)
    else:
      parent.replace(target, list)


#-----------FACTORY FUNCTIONS-----------#
PARSER = etree.XMLParser(remove_blank_text=False, remove_comments=False, ns_clean=True)
PARSER.set_element_class_lookup(etree.ElementDefaultClassLookup(
                                element=XmlTreeElement,
                                comment=XmlTreeComment))

def Element(name, attrib=None, nsmap=None, parent=None, text=None, 
            parser=PARSER):
  nsmap = nsmap or {}
  if not nsmap and hasattr(parent, 'nsmap'):
    nsmap = parent.nsmap
  nsmap.update({ 'xml' : XML_NS,
                 'xi'  : XI_NS })

  elem = parser.makeelement(name, attrib=attrib or {}, nsmap=nsmap)
  elem.text = text or ''
  if parent is not None:
    parent.append(elem)
  return elem

def uElement(name, attrib=None, nsmap=None, parent=None, text=None, **kwargs):
  # the below is more elegant, but won't work because Elements subclass
  # list, and lists evaluate to false when empty
  #
  # return parent.getxpath(name, None) or Element(name, parent=parent, **kwargs)
  elem = parent.getxpath(name, None)
  if elem is None:
    elem = Element(name, parent=parent, attrib=attrib, text=text, **kwargs)
  else:
    if text is not None:
      elem.text = text
    if attrib:
      for k,v in attrib.items():
        if v:
          elem.attrib[k] = v
        else:
          del(elem.attrib[k])
  return elem

def parse(file, parser=PARSER, base_url=None, xinclude=False, macros={}, 
                remove_macros=False): 
  try:
    roottree = etree.parse(file, parser, base_url=base_url)
  except etree.XMLSyntaxError, e:
    raise errors.XmlSyntaxError(file, e)

  #remove comments - do this early to avoid macro resolution in comments
  for elem in roottree.getroot().iterdescendants():
    if isinstance(elem, etree.CommentBase):
      elem.getparent().remove(elem)
 
  # process xincludes
  if xinclude:
    roottree.getroot().xinclude(macros=macros)

  if remove_macros:
    roottree.getroot().remove_macros()

  # remove unused namespaces (i.e. XInclude)
  etree.cleanup_namespaces(roottree)

  return roottree

def fromstring(s, **kwargs):
  root = parse(StringIO(s), **kwargs).getroot()
  root.base = None
  return root
