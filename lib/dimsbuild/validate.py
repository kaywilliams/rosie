from StringIO import StringIO
from lxml     import etree

import copy
import os

from dims import xmllib

class BaseConfigValidator:
  def __init__(self, schemaspath, config):
    self.schemaspath = schemaspath
    self.config = config

  def validate(self, xpath_query, schema_file=None, schema_contents=None):
    if (schema_file is None and schema_contents is None) or \
           (schema_file is not None and schema_contents is not None):
      raise RuntimeError("either the schema file or the schema contents must be specified")

    cwd = os.getcwd()
    os.chdir(self.schemaspath)
    try:
      try:
        trees = self.getXmlSection(xpath_query)
        if len(trees) == 0:
          return
        if len(trees) != 1:
          raise InvalidConfigError(self.config.file,
                "multiple instances of '%s' element found" % trees[0].tag)
        if schema_contents is None:
          schema_contents = self.readSchema(schema_file)
        schema_tree = self.massageSchema(schema_contents,
                                         trees[0].tag,
                                         schema_file)
        schema = etree.fromstring(str(schema_tree))
        relaxng = etree.RelaxNG(etree.ElementTree(schema))
      except etree.RelaxNGParseError, e:
        raise InvalidSchemaError(schema_file or '<string>', e.error_log)
      else:
        if not relaxng.validate(self.config):
          if schema_file is not None:
            raise InvalidConfigError(self.config.getroot().file, relaxng.error_log, schema_file)
          else:
            raise InvalidConfigError(self.config.getroot().file, relaxng.error_log)
    finally:
      os.chdir(cwd)

  def readSchema(self, filename):
    schema_file = self.schemaspath / filename
    if not schema_file.exists():
      raise IOError("missing schema file '%s' at '%s'" % (filename, schema_file.dirname))

    schema = xmllib.tree.read(filename)
    ## FIXME: xmltree/lxml seems to be losing the xmlns attribute
    schema.getroot().attrib['xmlns'] = "http://relaxng.org/ns/structure/1.0"
    return str(schema)

  def massageSchema(self, schema_contents, tag, schema_file):
    schema = xmllib.tree.read(StringIO(schema_contents))
    ## FIXME: xmltree/lxml seems to be losing the xmlns attribute
    schema.getroot().attrib['xmlns'] = "http://relaxng.org/ns/structure/1.0"
    return schema

  def getXmlSection(self, query):
    return self.config.xpath(query, [])

class MainConfigValidator(BaseConfigValidator):
  def __init__(self, schemaspath, config):
    BaseConfigValidator.__init__(self, schemaspath, config)

class ConfigValidator(BaseConfigValidator):
  def __init__(self, schemaspath, config):
    BaseConfigValidator.__init__(self, schemaspath, config)
    self.xpaths = []

  def getXmlSection(self, query):
    self.xpaths.append(query)
    return BaseConfigValidator.getXmlSection(self, query)

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
        raise InvalidConfigError(self.config.getroot().file,
                                 " unknown element '%s' found in distro.conf" % \
                                 child.tag)

  def massageSchema(self, schema_contents, tag, schema_file):
    schema = BaseConfigValidator.massageSchema(self, schema_contents, tag, schema_file)
    tree = schema.get('//element[@name="distro"]')

    # add the 'schema-version' attribute to the distro element
    schemaver = xmllib.tree.Element('attribute',
                                    attrs={'name': 'schema-version'})
    choice = xmllib.tree.Element('choice', parent=schemaver)
    xmllib.tree.Element('value', parent=choice, text='1.0',
                        attrs={'type': 'string'})
    tree.insert(0, schemaver)

    elemschema = schema.get('//element[@name="%s"]' % tag)
    if elemschema is None:
      raise InvalidSchemaError(schema_file or '<string>',
      "the schema file doesn't define the %s element" % tag)
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
    if type(self.args[1]) == type(''):
      return self.args[1]
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
      return 'Validation of "%s" failed:\n' % self.args[0] + \
             InvalidXmlError.__str__(self)
class InvalidSchemaError(InvalidXmlError):
  def __str__(self):
    return 'Error parsing schema file "%s":\n' % self.args[0] + \
      InvalidXmlError.__str__(self)
