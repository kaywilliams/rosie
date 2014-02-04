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
from deploy.util import shlib

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
    result = XmlTreeElement.xpath(self, path, namespaces=namespaces,
                                        extensions=extensions)
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
    if not isinstance(elem, etree._Element) or not elem.tail:
      etree.ElementBase.remove(self, elem)

    else:
      # remove leading newline from tail for better whitespace management
      tail = re.sub(r'^\n', '', elem.tail)
      previous = elem.getprevious()

      if previous is not None:
        # add tail to previous elem tail
        previous.tail = (previous.tail or '') + tail
        etree.ElementBase.remove(self, elem)

      else:
        # add tail to self text
        self.text = (self.text or '') + tail
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

        # ignore tails
        if (isinstance(v, etree._ElementStringResult) and 
            v.is_tail and v.getparent() in value):
          continue

        # if previous sibling, add text to previous sibling tail
        if child.getprevious() is not None:
          child.getprevious().tail = (child.getprevious().tail or '') + v

        # else add text to parent element text
        else:
          self.text = (self.text or '') + v

      else:
        if isinstance(v, etree.ElementBase):
          child.addprevious(v)

    self.remove(child)

  def resolve_macros(self, find=False, map={}, placeholder_xpath='.',
                     defaults_file=None):
    """
    Processes macro definitions and resolves macro variables.  Macro
    definitions take one of two forms:

    * <macro id='name'>value</macro>
    * <macro id='name' type='script'>script</macro>
    
    The first provides the macro value as static text. The second allows
    providing a dynamic default value that is initialized by executing the
    script. The generated value is stored for subsequent use in the
    'defaults_file' provided as a method attribute.

    Macros can exist at any level of the element. Macro variables use the
    syntax '%{macroid}'. Macro variables can occur in element nodes and
    attributes.

    Keyword arguments:
    find -- a boolean value indicating whether macro definitions should be
    discovered  and removed from the element and its descendants.  The default
    value is False.
    
    map -- a dictionary in placeholder:value format for use in resolving
    macros. Values can be one of three types:
    
    * string - a string value, e.g. 'text'
    * macro_element - a macro element , e.g. fromstring('<macro>...</macro>')
    * macro_resolution_function - a function that accepts two parameters
      placeholder and string, and returns a resolved string. See the 
      resolve_search_path_macro function in this file for an example.

        map = {'%{name1}: string,
                %{name2}: macro_elem,
                %{name3}: macro_resolution_function}

    Provided macros take precedence over found macros.

    placeholder_xpath -- query providing path to the root element to
    be searched for macro placeholders. If not provided, the current
    element will be searched. If the xpath does not return an element,
    resolve macros will return silently.

    defaults_file -- string or tuple containing information for a file used for
    storing and retrieving default values. A few notes regarding the
    defaults_file:

    * If a string is provided, it is used as the path for the file. If a tuple
    is provided, it must contain two items. The first item is a string
    containing % operators, e.g.  'path/%s.dat'. The second item is a list
    containing xpath query strings used for resolving % operators, e.g.
    ['./main/id/text()']. 

    * the defaults_file name is resolved after resolving all static macros and 
    just prior to resolving any dynamic-default macros.

    * If the defaults_file does not exist, it will be created.

    * If macro definitions containing scripts exist and a defaults_file
    has not been provided, an error will be raised. 

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
      for elem in etree.ElementBase.xpath(self, '//macro'): 
        # ignore parent macros (until later loops)
        if [ x for x in elem.iterchildren('macro') ]:
          continue

        # validate element
        if not 'id' in elem.attrib:
          message = "Missing required 'id' attribute."
          raise errors.MacroError(self.getroot().base, message, elem)

        if re.findall(MACRO_REGEX, elem.attrib['id']):
          message = "Macros not allowed in macro ids."
          raise errors.MacroError(self.getroot().base, message, elem)

        valid = ['id', 'type', '{%s}base' % XML_NS ] 
        invalid =  set(elem.attrib.keys()) - set(valid)
        if invalid:
          if len(invalid) == 1:
            message = ("Invalid attribute '%s' in macro element." % 
                        invalid.pop())
          else:
            message = ("Invalid attributes '%s' in macro element." %
                       "', '".join(invalid))
          raise errors.MacroError(self.getroot().base, message, elem)
  
        # valid type values?
        if 'type' in elem.attrib and elem.attrib['type'] not in \
                                        ['text', 'script']:
          message = ("Invalid value for attribute 'type'. Valid values "
                     "are 'text' and 'script'.")
          raise errors.MacroError(self.getroot().base, message, elem)
  
        # script provided?
        if 'type' in elem.attrib and not elem.text.strip():
          message = "No script provided."
          raise errors.MacroError(self.getroot().base, message, elem) 
 
        # add elem to map
        name = '%%{%s}' % elem.attrib['id']
        if name not in map: # higher level macros trump lower ones
          value = elem

          # check for circular references
          if name in etree.tostring(value, with_tail=False):
            message = ("Macro value contains a circular reference to "
                       "the macro id.")
            raise errors.MacroError(self.getroot().base, message, elem)
  
          # add elem value to macros
          map[name] = value 
 
    if not map: # no macros to resolve
      return

    unknown = set() # macro references with no corresponding definition
    waiting = set() # macro references that cannot be resolved until 
                    # defaults_file name is resolved

    unresolved_strings = set() #strings with macro resolution errors

    while True:
      remaining = {}

      for macro in set(re.findall(MACRO_REGEX,
                       etree.tostring(search_elem))).difference(unknown):
        remaining[macro] = {'attrib_strings': [],
                            'text_strings': [],}

      if not remaining:
        break

      remaining_strings = set()

      # get remaining strings
      for macro in remaining:
        # ignore unknown
        if not macro in map:
          unknown.add(macro)
          continue

        for s in [ x for x in etree.ElementBase.xpath(search_elem, './/@*') 
          if macro in x ]:
          remaining[macro]['attrib_strings'].append(s)
          remaining_strings.add(s)

        for s in etree.ElementBase.xpath(search_elem,
          ".//text()[re:test(., '.*%s.*', 'g')]" % macro,
          namespaces={'re':RE_NS}):
          remaining[macro]['text_strings'].append(s)
          remaining_strings.add(s)
            
      for macro in remaining:
        # text and tails
        for string in remaining[macro]['text_strings']:
          parent = string.getparent()

          # macro is string
          if isinstance(map[macro], basestring):
            if string.is_text:
              parent.text = string.replace(macro, map[macro])
            if string.is_tail:
              parent.tail = string.replace(macro, map[macro])
            if string in unresolved_strings: unresolved_strings.remove(string)

          # macro is function
          elif hasattr(map[macro], '__call__'):
            newstring = map[macro](macro, string)
            if self._validate_resolved_macro(macro, string, newstring, 
                unresolved_strings, remaining_strings, parent):
              if string.is_text: parent.text = newstring
              if string.is_tail: parent.tail = newstring

          # macros is macro element
          else:
            # resolve script values
            if 'type' in map[macro].attrib and \
               map[macro].attrib['type'] == 'script':
              try:
                map[macro] = self._get_macro_value(map[macro], defaults_file)
                waiting.discard(macro)
              except errors.MacroDefaultsFileNameUnresolved as e:
                waiting.add(macro)
                if set(remaining.keys()) == waiting: raise
              continue

            # resolve text values 
            text, tail = string.split(macro, 1)
            elems = [ x.copy() for x in map[macro] ]
            elems.reverse()

            if string.is_text:
              parent.text = text + (map[macro].text or '')
              for elem in elems:
                parent.insert(0, elem)
              if elems:
                elems[0].tail = (elems[0].tail or '') + tail 
              else:
                parent.text += tail

            if string.is_tail:
              grandparent = parent.getparent()
              parent.tail = text + (map[macro].text or '')
              for elem in elems:
                grandparent.insert(grandparent.index(parent) + 1, elem)
              if elems:
                elems[0].tail = (elems[0].tail or '') + tail
              else:
                parent.tail += tail

            if elems: 
              # creating new elems invalidates the original string, so
              # remove it from all macros in this loop.
              for r in remaining:
                if string in remaining[r]['text_strings']:
                  remaining[r]['text_strings'].remove(string)
 
            if string in unresolved_strings: unresolved_strings.remove(string)

        # attributes
        for string in remaining[macro]['attrib_strings']:
          parent = string.getparent()
          if string in parent.values(): # ignore previously changed strings
            id = [ k for k,v in parent.items() if string == v][0]

          # macros is string
          if isinstance(map[macro], basestring):
            parent.attrib[id] = string.replace(macro, map[macro])
            if string in unresolved_strings: unresolved_strings.remove(string)

          # macro is function
          elif hasattr(map[macro], '__call__'):
            newstring = map[macro](macro, string)
            if self._validate_resolved_macro(macro, string, newstring, 
                unresolved_strings, remaining_strings, parent):
              parent.attrib[id] = newstring
         
          # macro is macro elem
          else:
            parent.attrib[id] = string.replace(macro, 
                                 map[macro].getxpath('./text()', '""'))
            if string in unresolved_strings: unresolved_strings.remove(string)

    return map

  def _get_macro_value(self, macro, defaults_file):
    # read defaults_file
    defaults_file = self.get_macro_defaults_file(defaults_file)
    if not defaults_file:
      raise errors.MacroDefaultsFileNotProvided

    if defaults_file.exists():
      root = parse(defaults_file).getroot()
    else:
      try:
        defaults_file.dirname.mkdirs()
      except (pps.Path.error.PathError), e:
        raise errors.MacroUnableToCreateFile(defaults_file, e)
      root = Element('xml')

    if not root.xpath('./macros'):
      Element('macros', parent=root)

    defaults = root.getxpath('./macros')

    # get default value
    elem = defaults.getxpath('./macro[@id="%s"]' % macro.attrib['id'], None)

    # delete stored value if script has changed
    if elem is not None and \
       elem.getxpath('script/text()', '').strip() != macro.text.strip():
      defaults.remove(elem)
      elem = None

    # retrieve stored value
    if elem is not None:
      value = elem.getxpath('value/text()', '')

    # generate new value
    else:
      script_file = pps.path(defaults_file.dirname/'.script')
      script_file.write_text(macro.text.encode('utf8').lstrip())
      script_file.chmod(0750)
      try:
        value = '/n'.join(shlib.execute(script_file))
      except shlib.ShExecError as e:
        raise errors.MacroScriptError(macro.getroot().base, macro, 
                                      script_file, e)

      script_file.rm(force=True)

      # save default value
      parent = Element('macro', attrib={'id': macro.attrib['id']}, 
                               parent=defaults)
      Element('script', text=macro.text, parent=parent)
      Element('value', text=value, parent=parent)
      XmlTreeElement.write(defaults.getroot(), defaults_file)

    return value 

  def get_macro_defaults_file(self, defaults_file):
    # defaults_file is None
    if not defaults_file: return defaults_file

    # defaults_file is a string
    if isinstance(defaults_file, basestring): return pps.path(defaults_file)

    # defaults_file is a tuple
    try:
      namestring = defaults_file[0]
      namevalues = [eval('self.getxpath("%s")' % x) for x in defaults_file[1]]
      defaults_file = pps.path(namestring % tuple(namevalues))
    except errors.XmlPathError, e:
      raise errors.MacroDefaultsFileXmlPathError(str(e))

    if re.findall(MACRO_REGEX, defaults_file):
      raise errors.MacroDefaultsFileNameUnresolved(defaults_file)

    return defaults_file

  def remove_macros(self, defaults_file=None):
    macros = etree.ElementBase.xpath(self, './/macro')

    for elem in macros:
      elem.getparent().remove(elem)

    defaults_file = self.get_macro_defaults_file(defaults_file)
    if not (defaults_file and defaults_file.exists()): return
      
    # cleanup old macro values from defaults file
    stored_macros = parse(defaults_file).getroot()

    existing = set(stored_macros.xpath('./macros/macro/@id', []))
    expected = set([ x.attrib['id'] for x in macros ])

    remove = existing - expected
    for id in remove:
      elem = stored_macros.getxpath('./macros/macro[@id="%s"]' % id)
      elem.getparent().remove(elem)

    XmlTreeElement.write(stored_macros, defaults_file)

  def _validate_resolved_macro(self, macro, currstring, newstring, 
                               unresolved_strings, remaining_strings, elem):
    if currstring == newstring: # fail
      if unresolved_strings == remaining_strings:
        raise errors.MacroError(self.getroot().base, '', elem) 
      unresolved_strings.add(currstring)
      return False
    else: # success
      if currstring in unresolved_strings:
        unresolved_strings.remove(currstring)
      return True

  def write(self, file):
    file = pps.path(file)
    if not file.exists: file.mknod()

    f = codecs.open(file, encoding='utf-8', mode='w')
    f.write(self.unicode())
 
  def xinclude(self, macros={}, macro_defaults_file=None):
    """
    XInclude processor with integrated support for macro resolution
    """

    hrefs = {} # cache of previously included files

    # resolve macros
    macros = self.resolve_macros(find=True, map=macros, 
                                 defaults_file=macro_defaults_file) 

    while True:
      elems = self.xpath('//xi:include', [], namespaces=({'xi': XI_NS}))

      if not elems:
        # resolve macros one last time after xincludes are processed
        # to catch any late-defined macros
        self.resolve_macros(map=macros, defaults_file=macro_defaults_file)
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
            href = pps.path(elem.attrib['href'])
            href = (base.dirname / href).normpath()

            if base == href:
              raise errors.XIncludeError(message='The file contains a '
                                                 'recursive include to '
                                                 'itself' , elem=elem)

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
                               macro_defaults_file=self.get_macro_defaults_file(
                                                   macro_defaults_file),
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
                  isinstance(x, basestring) ]
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

def parse(file, parser=PARSER, base_url=None, xinclude=False, 
                resolve_macros=False, macros={}, 
                remove_macros=False, macro_defaults_file=None): 
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
    roottree.getroot().xinclude(macros=macros, 
                                macro_defaults_file=macro_defaults_file)
  elif resolve_macros:
    roottree.getroot().resolve_macros(find=True,
                                      map=macros, 
                                      defaults_file=macro_defaults_file)

  if remove_macros:
    roottree.getroot().remove_macros(defaults_file=macro_defaults_file)

  # remove unused namespaces (i.e. XInclude)
  etree.cleanup_namespaces(roottree)

  return roottree

def fromstring(s, **kwargs):
  root = parse(StringIO(s), **kwargs).getroot()
  root.base = None
  return root


#-----------MACRO RESOLVER FUNCTIONS-----------#

def resolve_search_path_macro(placeholder, string):
  """
  Function that can be provided in a macro map (see 
  XmlTreeElement.resolve_macros method) for resolving pps search_path macros.

  Requires a search path handler to be established prior to use. See the
  pps.search_paths module for information.

  Accepts two parameters:
  
  * placeholder - The macro placeholder to be replaced, e.g. 
                  '%{templates_dir}'
  * string      - An _ElementStringResult containing the placeholder, e.g. 
                  'Here is a path to a file: %{templates_dir}/some/file.txt"

  Returns a copy of the string with the placeholder resolved.
  """
  for substring in string.split():
    if placeholder in substring:
      replaced = pps.path(substring, 
                          search_path_ignore=[string.getparent().base])
      string = string.replace(substring, replaced)
      break

  return string
