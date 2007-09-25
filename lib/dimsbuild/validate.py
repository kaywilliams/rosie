import copy
import os

from lxml import etree

from dims import filereader
from dims import xmltree

class ValidateMixin:
  def __init__(self, schemaspath, config):
    self.schemaspath = schemaspath
    self.config = config

  def validate(self, xpath_query, schemafile=None, schemacontents=None):
    if (schemafile is None and schemacontents is None) or \
           (schemafile is not None and schemacontents is not None):
      raise RuntimeError("either the schema file or the schema contents must be specified")
    
    cwd = os.getcwd()
    os.chdir(self.schemaspath)
    try:
      schemacontents = schemacontents or self.getSchema(schemafile)
      try:
        schema = etree.RelaxNG(etree.ElementTree(etree.fromstring(schemacontents)))
      except etree.RelaxNGParseError, e:
        if schemafile is not None:
          raise InvalidSchemaError(schemafile, e.error_log)
        else:
          raise InvalidSchemaError('<string>', e.error_log)
      
      doc = self.getXmlSection(xpath_query)
      if not schema.validate(doc):
        if schemafile is not None:
          raise InvalidConfigError(self.config.file, schema.error_log, schemafile)
        else:
          raise InvalidConfigError(self.config.file, schema.error_log)
    
    finally:
      os.chdir(cwd)
  
  def getSchema(self, filename):
    schema = self.schemaspath / filename
    if schema.exists():
      return '\n'.join(filereader.read(schema))
    else:
      raise IOError("missing schema file '%s' at '%s'" % (filename, schema.dirname))
  
  def _strip_macro_elements(self, tree):
    for macro in tree.xpath('//macro', []):
      tree.remove(macro)

class MainConfigValidator(ValidateMixin):
  def __init__(self, schemaspath, config):
    ValidateMixin.__init__(self, schemaspath, config)

  def getXmlSection(self, xpath_query):
    tree = copy.deepcopy(self.config.get(xpath_query, None))
    self._strip_macro_elements(tree)
    return tree
    
class ConfigValidator(ValidateMixin):
  def __init__(self, schemaspath, config, elogger):
    ## FIXME: adding '/distro/macro' is a hack    
    self.xpaths = ['/distro/macro']
    self.elogger = elogger
    
    ValidateMixin.__init__(self, schemaspath, config)
  
  def getXmlSection(self, xpath_query):
    parent = xmltree.Element('distro', parent=None)
    trees = self.config.xpath(xpath_query, [])
    if len(trees) > 1:
      self.raiseInvalidConfig("multiple instances of '%s' element found "
                              "in distro.conf" % trees[0].tag)
    if len(trees) == 0:
      return parent

    # save the xpath query so that you can check the top level
    # elements later on.    
    self.xpaths.append(xpath_query)
    
    tree = copy.deepcopy(trees[0])
    tree.parent = parent
    self._strip_macro_elements(tree)
    parent.append(tree)
    return parent

  def validateElements(self):
    elements = []
    for xpath in self.xpaths:
      element = self.config.get(xpath, None)
      if element is not None:
        while element.getparent() != element.getroot():
          element = element.getparent()
        if element not in elements:
          elements.append(element)
    for child in self.config.getroot().iterchildren():
      if child.tag is etree.Comment: continue
      if child not in elements:
        self.elogger.log(2, "WARNING: unknown element '%s' found in distro.conf" % child.tag)

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
      return 'Validation of "%s" failed:\n' % self.args[0] + \
        InvalidXmlError.__str__(self)
class InvalidSchemaError(InvalidXmlError):
  def __str__(self):
    return 'Error parsing schema file "%s":\n' % self.args[0] + \
      InvalidXmlError.__str__(self)
