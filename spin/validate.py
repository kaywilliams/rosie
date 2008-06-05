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
from lxml import etree

import copy
import os

from rendition import rxml

NSMAP = {'rng': 'http://relaxng.org/ns/structure/1.0'}

class BaseConfigValidator:
  def __init__(self, schema_paths, config_path):
    self.schema_paths = schema_paths
    self.config = rxml.tree.read(config_path, xincluder=rxml.xinclude.MacroXInclude())
    self.elements = []

    self.curr_schema = None

  def validate(self, xpath_query, schema_file=None, schema_contents=None):
    if schema_file and schema_contents:
      raise IOError("The 'schema_file' and the 'schema_contents' parameters "\
                    "are mutually exclusive.")
    if schema_file is None and schema_contents is None:
      raise IOError("Either the 'schema_file' or the 'schema_contents' parameter "\
                    "should be provided.")
    self.elements.append(xpath_query.lstrip('/'))
    tree = self.config.get(xpath_query)
    if schema_contents:
      self.validate_with_string(schema_contents, tree, self.elements[-1])
    else:
      self.validate_with_file(schema_file, tree, self.elements[-1])

  def validate_with_string(self, schema_contents, tree, tag):
    schema = etree.fromstring(schema_contents, base_url=self.config.file.dirname)
    if tree is None:
      self.check_required(schema, tag)
      return
    schema_tree = self.massage_schema(schema, tag)
    self.relaxng(schema_tree, tree)

  def validate_with_file(self, schema_file, tree, tag):
    self.curr_schema = None
    file = None
    for path in self.schema_paths:
      file = path/schema_file
      if file.exists():
        break
      else:
        file = None
    if not file:
      return # no schema file
    self.curr_schema = file
    schema = self._read_schema()
    if tree is None:
      self.check_required(schema, tag)
      return
    schema_tree = self.massage_schema(schema, tag)
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

  def _read_schema(self):
    cwd = os.getcwd()
    os.chdir(self.curr_schema.dirname)
    try:
      schema = rxml.tree.read(self.curr_schema.basename)
    finally:
      os.chdir(cwd)
    return schema

  def massage_schema(self, schema, tag):
    return schema

  def check_required(self, schema, tag):
    distro_defn = schema.get('//rng:element[@name="distro"]', namespaces=NSMAP)
    if distro_defn is not None:
      optional = distro_defn.get('rng:optional', namespaces=NSMAP)
      if optional is None:
        raise InvalidConfigError(self.config.getroot().file,
                                 "Missing required element: '%s'" % tag)

class MainConfigValidator(BaseConfigValidator):
  def __init__(self, schema_paths, config_path):
    BaseConfigValidator.__init__(self, schema_paths, config_path)

class ConfigValidator(BaseConfigValidator):
  def __init__(self, schema_paths, config_path):
    config = rxml.tree.read(config_path, xincluder=rxml.xinclude.MacroXInclude())
    BaseConfigValidator.__init__(self, schema_paths, config_path)

  def verify_elements(self, disabled):
    processed = []
    for child in self.config.getroot().iterchildren():
      if child.tag is etree.Comment: continue
      if child.tag in disabled: continue
      if child.tag not in self.elements:
        raise InvalidConfigError(self.config.getroot().file,
                                 " unknown element '%s' found:\n%s"
                                 % (child.tag, child.tostring(lineno=True)))
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
    if isinstance(self.args[1], basestring):
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
