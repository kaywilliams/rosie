from StringIO import StringIO
from lxml     import etree

import copy
import os

from dims import xmllib

class BaseConfigValidator:
  def __init__(self, schema_paths, config):
    self.schema_paths = schema_paths
    self.config = config
    self.elements = []

    self.curr_schema = None

  def validate(self, xpath_query, schema_file=None, schema_contents=None):
    if (schema_file and schema_contents) or \
       (not schema_file and not schema_contents):
      raise RuntimeError("either the schema file or the schema contents must be specified")
    if not self.config.pathexists(xpath_query):
      return
    if schema_contents is None:
      schema_contents = self.read_schema(schema_file)
    cwd = os.getcwd()
    os.chdir(self.curr_schema.dirname)
    try:
      try:
        tree = self.config.get(xpath_query)
        self.elements.append(tree.tag)
        schema_tree = self.massage_schema(schema_contents, tree.tag, schema_file)
        schema = etree.fromstring(str(schema_tree))
        relaxng = etree.RelaxNG(etree.ElementTree(schema))
      except etree.RelaxNGParseError, e:
        raise InvalidSchemaError(self.curr_schema or '<string>', e.error_log)
      else:
        if not relaxng.validate(tree):
          if schema_file:
            raise InvalidConfigError(self.config.getroot().file, relaxng.error_log, self.curr_schema)
          else:
            raise InvalidConfigError(self.config.getroot().file, relaxng.error_log)
    finally:
      os.chdir(cwd)

  def read_schema(self, filename):
    self.curr_schema = None
    for path in self.schema_paths:
      schema_file = path/filename
      if not schema_file.exists():
        continue
      self.curr_schema = schema_file
    if not self.curr_schema:
      raise IOError("missing schema file '%s' at '%s'" % (filename, schema_file.dirname))
    schema = xmllib.tree.read(self.curr_schema)
    ## FIXME: xmltree/lxml seems to be losing the xmlns attribute
    schema.getroot().attrib['xmlns'] = "http://relaxng.org/ns/structure/1.0"
    return str(schema)

  def massage_schema(self, schema_contents, tag, schema_file):
    schema = xmllib.tree.read(StringIO(schema_contents))
    ## FIXME: xmltree/lxml seems to be losing the xmlns attribute
    schema.getroot().attrib['xmlns'] = "http://relaxng.org/ns/structure/1.0"
    return schema

class MainConfigValidator(BaseConfigValidator):
  def __init__(self, schema_paths, config):
    BaseConfigValidator.__init__(self, schema_paths, config)

class ConfigValidator(BaseConfigValidator):
  def __init__(self, schema_paths, config):
    BaseConfigValidator.__init__(self, schema_paths, config)

  def verify_elements(self, disabled):
    processed = []
    for child in self.config.getroot().iterchildren():
      if child.tag is etree.Comment: continue
      if child.tag in disabled: continue
      if child.tag not in self.elements:
        raise InvalidConfigError(self.config.getroot().file,
                                 " unknown element '%s' found" % child.tag)
      if child.tag in processed:
        raise InvalidConfigError(self.config.getroot().file,
                                 " multiple instances of the '%s' element "
                                 "found " % child.tag)
      processed.append(child.tag)

  def massage_schema(self, schema_contents, tag, schema_file):
    schema = BaseConfigValidator.massage_schema(self, schema_contents, tag, schema_file)
    distro_defn = schema.get('//element[@name="distro"]')
    start_elem  = distro_defn.getparent()
    for defn in distro_defn.iterchildren():
      if defn.tag == 'optional':
        for child in defn.iterchildren():
          start_elem.append(child)
          child.parent = start_elem
      else:
        start_elem.append(defn)
        defn.parent = start_elem
    start_elem.remove(start_elem.get('element[@name="distro"]'))
    return schema

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
      return 'Validation of "%s" failed: \n' % self.args[0] + \
             InvalidXmlError.__str__(self)
class InvalidSchemaError(InvalidXmlError):
  def __str__(self):
    return 'Error parsing schema file "%s":\n' % self.args[0] + \
      InvalidXmlError.__str__(self)
