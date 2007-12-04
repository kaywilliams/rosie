from StringIO import StringIO
from lxml     import etree

import copy
import os

from dims import xmllib

NSMAP = {'rng': 'http://relaxng.org/ns/structure/1.0'}

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
    tree = self.config.get(xpath_query)
    self.elements.append(tree.tag)
    if schema_contents:
      self.validate_with_string(schema_contents, tree)
    else:
      self.validate_with_file(schema_file, tree)

  def validate_with_string(self, schema_contents, tree):
    schema = etree.fromstring(schema_contents, base_url=self.config.filename.dirname)
    schema_treeself.massage_schema(schema, tree.tag)
    self.relaxng(schema_tree, tree)

  def validate_with_file(self, schema_file, tree):
    self.curr_schema = None
    for path in self.schema_paths:
      file = path/schema_file
      if file.exists():
        break
    self.curr_schema = file
    if not self.curr_schema:
      raise IOError("missing schema file '%s' at '%s'" % (file, file.dirname))
    schema_tree = self._read_schema(tree.tag)
    try:
      cwd = os.getcwd()
      os.chdir(self.curr_schema.dirname)
      self.relaxng(schema_tree, tree)
    finally:
      os.chdir(cwd)

  def relaxng(self, schema_tree, tree):
    try:
      relaxng = etree.RelaxNG(schema_tree)
    except etree.RelaxNGParseError, e:
      raise InvalidSchemaError(self.curr_schema or '<string>', e.error_log)
    else:
      if not relaxng.validate(tree):
        raise InvalidConfigError(self.config.getroot().file, relaxng.error_log,
                                 self.curr_schema or '<string>', tree.tostring(lineno=True))

  def _read_schema(self, tag):
    cwd = os.getcwd()
    os.chdir(self.curr_schema.dirname)
    try:
      schema = xmllib.tree.read(self.curr_schema.basename)
    finally:
      os.chdir(cwd)
    return self.massage_schema(schema, tag)

  def massage_schema(self, schema, tag):
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
        if child.tag == 'include':
          raise InvalidConfigError(self.config.getroot().file,
          "Unknown element '%s' found. Perhaps you need to include an XInclude\nnamespace declaration, e.g. xmlns:xi=\"http://www.w3.org/2001/XInclude\",\nin your config file:\n%s" % (child.tag, child))
        else:
          raise InvalidConfigError(self.config.getroot().file,
                                   " unknown element '%s' found:\n%s"
                                   % (child.tag, child))
      if child.tag in processed:
        raise InvalidConfigError(self.config.getroot().file,
                                 " multiple instances of the '%s' element "
                                 "found " % child.tag)
      processed.append(child.tag)

  def massage_schema(self, schema, tag):
    schema = BaseConfigValidator.massage_schema(self, schema, tag)
    distro_defn = schema.get('//rng:element[@name="distro"]', namespaces=NSMAP)
    start_elem  = distro_defn.getparent()
    for defn in distro_defn.iterchildren():
      start_elem.append(defn)
      defn.parent = start_elem
    start_elem.remove(start_elem.get('rng:element[@name="distro"]', namespaces=NSMAP))
    for opt_elem in start_elem.xpath('rng:optional', fallback=[], namespaces=NSMAP):
      for child in opt_elem.iterchildren():
        start_elem.append(child)
        child.parent = start_elem
      start_elem.remove(opt_elem)
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
    if len(self.args) == 4:
      return 'Validation of "%s" against "%s" failed. The invalid section is:\n%s\n' % \
        (self.args[0], self.args[2], self.args[3]) + InvalidXmlError.__str__(self)
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
