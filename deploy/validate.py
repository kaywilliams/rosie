#
# Copyright (c) 2015
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
from lxml import etree
from StringIO import StringIO

import copy
import os
import sys

from deploy.errors import DeployError, DeployEventError
from deploy.util   import pps
from deploy.util   import rxml

XmlTreeElement = rxml.tree.XmlTreeElement

from deploy.dlogging import L0, L1

NSMAP = {'rng': 'http://relaxng.org/ns/structure/1.0'}

class DeployValidationHandler:
  def validate_configs(self):
    try:
      self._validate_configs()
    except InvalidSchemaError, e:
      raise DeployError("Schema file used in validation appears to be invalid:\n%s" % e)
 
    except InvalidConfigError, e:
      raise DeployError("Validation against schema failed:\n%s" % e)
    except (InvalidXmlError, rxml.errors.ConfigError), e:
      raise DeployError(e)
    except DeployError:
      raise
    except Exception, e:
      raise
      raise DeployError("Unhandled exception while performing validation: %s" % e)
 

  def _validate_configs(self):
    "Validate deploy config and definition"

    if self.mainconfig.base is not None:
      self.logger.log(4, L0("Validating '%s'" % self.mainconfig.base))
    else:
      self.logger.log(4, L0("Validating main config with default settings"))

    v = MainConfigValidator([ x/'schemas' for x in self.sharedirs ],
                            self.mainconfig)
    v.validate('/deploy', schema_file='deploy.rng')

    # validate individual sections of the definition
    self.logger.log(4, L0("Validating '%s'" % pps.path(self.definition.base)))
    v = DefinitionValidator([ x/'schemas/definition' for x in self.sharedirs ],
                           self.definition)

    # expand macros - per event, depth first
    unresolved = [event for event in self.dispatch]
    while unresolved:
      event = unresolved.pop()

    # validate all top-level sections
    tle_elements = set() # list of already-validated modules (so we don't revalidate)
    for event in self.dispatch:
      moduleid = event.__module__.split('.')[-1]

      # resolve macros
      macros = self.initial_macros
      macros.update(getattr(event, 'macros', {}))
      macros['%{module}'] = moduleid
      self.definition.resolve_macros(map=macros,
                                     placeholder_xpath='/*/%s' % moduleid)

      # validate config
      if moduleid in tle_elements: continue # don't re-validate
      v.validate(moduleid, schema_file='%s.rng' % moduleid, required=False)
      if self.definition.pathexists(moduleid):
        tle_elements.add(moduleid)

    expected_elements = tle_elements.union(self.disabled_modules)
    expected_elements.add('all')
    self._verify_tle_elements(expected_elements)

    # allow events to validate other things not covered in schemas
    for event in self.dispatch:
      if event.enabled:
        try:
          event.validate()
        except DeployEventError, e:
          self._handle_Exception(e, event.id) 

  def _verify_tle_elements(self, expected_elements):
    processed = set()
    for child in self.definition.iterchildren():
      if child.tag is etree.Comment: continue
      if child.tag not in expected_elements:
        raise InvalidConfigError(self.definition.base,
          " unknown element '%s' found:\n%s" % (child.tag, child))
      if child.tag in processed:
        raise InvalidConfigError(self.definition.base,
                                 " multiple instances of the '%s' element "
                                 "found " % child.tag)
      processed.add(child.tag)


class BaseConfigValidator:
  def __init__(self, schema_paths, config):
    self.schema_paths = schema_paths
    self.config = config

    self.curr_schema = None

  def validate(self, xpath_query, required=True, schema_file=None, 
               schema_contents=None):
    if schema_file and schema_contents:
      raise AttributeError("'schema_file' and 'schema_contents' "
                           "are mutually exclusive.")
    if schema_file is None and schema_contents is None:
      raise AttributeError("Either 'schema_file' or 'schema_contents' "
                           "must be provided.")
    element = xpath_query.lstrip('/')
    tree = self._scrub_tree(self.config.getxpath(xpath_query, None))
    if schema_contents:
      self.validate_with_string(schema_contents, tree, element, required)
    else:
      self.validate_with_file(schema_file, tree, element, required)

  def _scrub_tree(self, tree):
    if tree is None: return

    # reparse the tree to get sequential sourcelines
    tree = rxml.tree.parse(StringIO(tree)).getroot()

    return tree

  def validate_with_string(self, schema_contents, tree, tag, required):
    schema = etree.fromstring(schema_contents)
    if tree is None:
      self.check_required(schema, tag, required)
      return
    schema_tree = self.massage_schema(schema, tag)
    self.relaxng(schema_tree, tree)

  def validate_with_file(self, schema_file, tree, tag, required):
    self.curr_schema = None
    file = None
    for path in self.schema_paths:
      file = path/schema_file
      if file.exists():
        break
      else:
        file = None
    if not file and required:
      raise MissingSchemaFileError(schema_file, 
                                   [str(p) for p in self.schema_paths])
    if not file and not required:
      return 
    self.curr_schema = file
    schema = self._read_schema()
    if tree is None:
      self.check_required(schema, tag, required)
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
        raise InvalidConfigError(self.config.base,
                                 relaxng.error_log,
                                 self.curr_schema or '<string>',
                                 XmlTreeElement.tostring(tree, lineno=True))

  def _read_schema(self):
    cwd = os.getcwd()
    os.chdir(self.curr_schema.dirname)
    try:
      schema = rxml.tree.parse(self.curr_schema.basename).getroot()
    finally:
      os.chdir(cwd)
    return schema

  def massage_schema(self, schema, tag):
    return schema

  def check_required(self, schema, tag, required):
    if required:
      raise InvalidConfigError(self.config.base,
                               "Missing required element '%s'." % tag)


class MainConfigValidator(BaseConfigValidator):
  pass


class DefinitionValidator(BaseConfigValidator):
  def __init__(self, schema_paths, config):
    BaseConfigValidator.__init__(self, schema_paths, config)

  def massage_schema(self, schema, tag):
    schema = BaseConfigValidator.massage_schema(self, schema, tag)
    defn = schema.getxpath('//rng:element[@name="definition"]', namespaces=NSMAP)
    start_elem  = defn.getparent()
    for tle in defn.iterchildren():
      start_elem.append(tle)
      tle.parent = start_elem
    start_elem.remove(start_elem.getxpath('rng:element[@name="definition"]', namespaces=NSMAP))
    for opt_elem in start_elem.xpath('rng:optional', fallback=[], namespaces=NSMAP):
      for child in opt_elem.iterchildren():
        start_elem.append(child)
        child.parent = start_elem
      start_elem.remove(opt_elem)

    return schema

  def check_required(self, schema, tag, *args, **kwargs):
    defn = schema.getxpath('//rng:element[@name="definition"]', namespaces=NSMAP)
    if defn is not None:
      optional = defn.getxpath('rng:optional', namespaces=NSMAP)
      if optional is None:
        raise InvalidConfigError(self.config.base,
                                 "Missing required element: '%s'" % tag)
 
#------ ERRORS ------#
class InvalidXmlError(StandardError):
  def __str__(self):
    if isinstance(self.args[1], basestring):
      return self.args[1]
    msg = '\nErrors:\n'
    for err in self.args[1]: # relaxNG error log object
      msg += 'line %d: %s\n' % (err.line, err.message)
    return msg

class InvalidConfigError(InvalidXmlError):
  def __str__(self):
    if len(self.args) == 4:
      return ('Validation of "%s" failed. The invalid section '
              'is:\n\n%s\n' % (self.args[0], self.args[3])
              + InvalidXmlError.__str__(self))
    if len(self.args) == 3:
      return 'Validation of "%s" against "%s" failed:\n' % \
        (self.args[0], self.args[2]) + InvalidXmlError.__str__(self)
    else:
      return 'Validation of "%s" failed: \n' % self.args[0] + \
             InvalidXmlError.__str__(self)

class MissingSchemaFileError(InvalidConfigError):
  def __init__(self, file, paths):
    self.file = file
    self.paths = paths
  def __str__(self):
    return ("Unable to locate the schema file '%s' in any of the schema "
            "paths: %s" % (self.file, self.paths)) 

class InvalidSchemaError(InvalidXmlError):
  def __str__(self):
    return 'Error parsing schema file "%s":\n' % self.args[0] + \
      InvalidXmlError.__str__(self)

class InvalidEventError(StandardError):
  def __init__(self, event, message):
    self.event = event
    self.message = message
  def __str__(self):
    return "Validation of the %s element failed:\n%s" % (self.event, 
                                                         self.message)

