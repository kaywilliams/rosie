from StringIO import StringIO
from lxml     import etree

import copy
import os

from dims import xmllib

class ValidateMixin:
  def __init__(self, schemaspath, configfile):
    self.schemaspath = schemaspath
    self.configfile = configfile
    self.config = xmllib.config.read(self.configfile)
    
  def validate(self, xpath_query, schemafile=None, schemacontents=None):
    if (schemafile is None and schemacontents is None) or \
           (schemafile is not None and schemacontents is not None):
      raise RuntimeError("either the schema file or the schema contents must be specified")
    
    cwd = os.getcwd()
    os.chdir(self.schemaspath)
    try:
      try:
        trees = self.getXmlSection(xpath_query)
        if len(trees) == 0:
          return
        if len(trees) != 1:
          raise InvalidConfigError(self.configfile,
                "multiple instances of '%s' element found" % trees[0].tag)
          
        if schemacontents is None:
          schemacontents = self.getSchemaContents(schemafile)
        schema = etree.fromstring(str(self.getSchema(schemacontents, trees[0].tag)))
        relaxng = etree.RelaxNG(etree.ElementTree(schema))
      except etree.RelaxNGParseError, e:
        if schemafile is not None:
          raise InvalidSchemaError(schemafile, e.error_log)
        else:
          raise InvalidSchemaError('<string>', e.error_log)
      else:
        if not relaxng.validate(self.config):
          if schemafile is not None:
            raise InvalidConfigError(self.configfile, relaxng.error_log, schemafile)
          else:
            raise InvalidConfigError(self.configfile, relaxng.error_log)    
    finally:
      os.chdir(cwd)
  
  def getSchemaContents(self, filename):
    schemafile = self.schemaspath / filename
    if not schemafile.exists():
      raise IOError("missing schema file '%s' at '%s'" % (filename, schema.dirname))

    schema = xmllib.tree.read(filename)
    ## FIXME: xmltree/lxml seems to be losing the xmlns attribute    
    schema.getroot().attrib['xmlns'] = "http://relaxng.org/ns/structure/1.0"
    return str(schema)
  
  def getSchema(self, schemacontents, tag):
    schema = xmllib.tree.read(StringIO(schemacontents))
    ## FIXME: xmltree/lxml seems to be losing the xmlns attribute
    schema.getroot().attrib['xmlns'] = "http://relaxng.org/ns/structure/1.0"
    return schema

  def getXmlSection(self, query):
    return self.config.xpath(query, [])    

class MainConfigValidator(ValidateMixin):
  def __init__(self, schemaspath, configfile):
    ValidateMixin.__init__(self, schemaspath, configfile)

class ConfigValidator(ValidateMixin):
  def __init__(self, schemaspath, configfile):
    ValidateMixin.__init__(self, schemaspath, configfile)
    self.xpaths = []

  def getXmlSection(self, query):
    self.xpaths.append(query)
    return ValidateMixin.getXmlSection(self, query)

  def validateElements(self, disabled):
    elements = []
    for xpath in self.xpaths:
      element = self.config.get(xpath, None)
      if element is not None:
        while element.getparent() != element.getroottree().getroot():
          element = element.getparent()
        if element not in elements:
          elements.append(element)    
    for child in self.config.getroot().iterchildren():
      if child.tag is etree.Comment: continue
      if child.tag in disabled: continue
      if child not in elements:
        raise InvalidConfigError(self.configfile,
                                 " unknown element '%s' found in distro.conf" % \
                                 child.tag)

  def getSchema(self, schemacontents, tag):
    schema = ValidateMixin.getSchema(self, schemacontents, tag)
    tree = schema.get('//element[@name="distro"]')

    # add the 'schema-version' attribute to the distro element
    schemaver = xmllib.tree.Element('attribute',
                                attrs={'name': 'schema-version'})
    choice = xmllib.tree.Element('choice', parent=schemaver)
    xmllib.tree.Element('value', parent=choice, text='1.0',
                    attrs={'type': 'string'})
    tree.insert(0, schemaver)

    
    elemschema = schema.get('//element[@name="%s"]' % tag)
    # add a definition for multiple attributes
    anyattr = xmllib.tree.Element('define', parent=schema.getroot(),
                              attrs={'name': 'attribute-anything'})
    zom = xmllib.tree.Element('zeroOrMore', parent=anyattr)
    attr = xmllib.tree.Element('attribute', parent=zom)
    xmllib.tree.Element('anyName', parent=attr)
    
    count = 0
    while elemschema.getparent().tag != 'start':
      if elemschema.tag == 'element':
        name = elemschema.attrib.get('name', None)
        if name is None:
          name = str(count+1)
          count = count + 1
        self._add_definitions(elemschema, id='anything-element-%s' % name,
                              ignore=name)
        self._add_references(elemschema, id='anything-element-%s' % name)

      if elemschema.tag == 'optional':
        # delete all <optional> elements, because at this point we know
        # for sure that the element we are validating exists in the
        # config file.
        for child in elemschema.iterchildren():
          child.parent = elemschema.getparent()
          elemschema.getparent().append(child)
        elemschema = elemschema.getparent()
        elemschema.remove(elemschema.get('optional'))
      else:
        elemschema = elemschema.getparent()
    return schema
  
  def _add_references(self, schema, id):
    schema.addprevious(xmllib.tree.Element('ref', attrs={'name': id}))
    schema.addnext(xmllib.tree.Element('ref', attrs={'name': id}))
    
  def _add_definitions(self, schema, id, ignore=None):
    # add a definition for multiple elements
    anyelem = xmllib.tree.Element('define', parent=schema.getroot(),
                              attrs={'name': id})
    zom = xmllib.tree.Element('zeroOrMore', parent=anyelem)
    choice = xmllib.tree.Element('choice', parent=zom)
    text = xmllib.tree.Element('text', parent=choice)
    elem = xmllib.tree.Element('element', parent=choice)
    name = xmllib.tree.Element('anyName', parent=elem)
    if ignore is not None:
      exelem = xmllib.tree.Element('except', parent=name)
      xmllib.tree.Element('name', parent=exelem, text=ignore)                      
    xmllib.tree.Element('ref', parent=elem,
                    attrs={'name': 'attribute-anything'})
    xmllib.tree.Element('ref', parent=elem,
                    attrs={'name': id})

#------ ERRORS ------#
class InvalidXmlError(StandardError):
  def __str__(self):
    msg = ''    
    for err in self.args[1]: # relaxNG error log object
      msg += '  line %d: %s\n' % (err.line, err.message)
    return msg
class InvalidConfigError(InvalidXmlError):
  def __str__(self):
    if len(self.args) == 3:
      return 'Validation of "%s" against "%s" failed:\n' % \
        (self.args[0], self.args[2]) + InvalidXmlError.__str__(self)
    else:
      if type(self.args[1]) == type(''):
        return 'Validation of "%s" failed:\n%s' % (self.args[0], self.args[1])
      else:
        return 'Validation of "%s" failed:\n' % self.args[0] + \
               InvalidXmlError.__str__(self)
class InvalidSchemaError(InvalidXmlError):
  def __str__(self):
    return 'Error parsing schema file "%s":\n' % self.args[0] + \
      InvalidXmlError.__str__(self)
