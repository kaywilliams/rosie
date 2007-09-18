import copy
import os

from lxml import etree

from dims import filereader
from dims import xmltree


class ValidateMixin:
  def __init__(self):
    self.schemaspath = self.SHARE_DIR/'schemas'
  
  def _validate(self, xquery, schemafile=None, schemacontents=None, what='distro'):
    if what != self.cvars.get('validate', 'distro'): return
    
    if (schemafile is None and schemacontents is None) or \
           (schemafile is not None and schemacontents is not None):
      raise RuntimeError("either the schema file or the schema contents should be specified")
    
    cwd = os.getcwd()
    os.chdir(self.schemaspath/'distro.conf')
    try:
      schemacontents = schemacontents or self.getSchema(schemafile)
      try:
        schema = etree.RelaxNG(etree.ElementTree(etree.fromstring(schemacontents)))
      except etree.RelaxNGParseError, e:
        print e.error_log.last_error
        why = e.error_log.last_error.message
        if schemafile is not None:
          raise InvalidSchemaError("%s: %s" %(schemafile, why))
        else:
          raise InvalidSchemaError(why)
      
      doc = self.getXmlSection(xquery)
      if not schema.validate(doc):
        why = schema.error_log.last_error.message
        if schemafile is not None:
          self.raiseInvalidConfig("validation of the %s.conf against the %s failed: %s" \
                                  % (self.cvars.get('validate', 'distro'), schemafile, why))
        else:
          self.raiseInvalidConfig("validation of the %s.conf failed: %s" \
                                  % (self.cvars.get('validate', 'distro', why)))
    finally:
      os.chdir(cwd)
  
  def raiseInvalidConfig(self, message):
    raise InvalidConfigError(message)
  
  def getSchema(self, filename):
    if self.cvars.get('validate', 'distro') == 'dimsbuild':
      schema = self.schemaspath/filename
    else:      
      schema = self.schemaspath/'distro.conf'/filename
      
    if schema.exists():
      return '\n'.join(filereader.read(schema))
    else:
      raise IOError, "missing file: '%s'" %(schema,)

  def getXmlSection(self, xquery):
    "Return the element in the tree with the xpath query provided."
    if self.cvars.get('validate', 'distro') == 'dimsbuild':
      return self._get_dimsbuild_section(xquery)
    else:
      return self._get_distro_section(xquery)

  def _get_dimsbuild_section(self, xquery):
    tree = copy.deepcopy(self._base.mainconfig.get(xquery, None))
    self._strip_macro_elements(tree)
    return tree
  
  def _get_distro_section(self, xquery):
    parent = xmltree.Element('distro', parent=None)
    tree = copy.deepcopy(self.config.get(xquery, None))
    
    if tree is not None:
      tree.parent = parent
      self._strip_macro_elements(tree)
      parent.append(tree)
    return parent
  
  def _strip_macro_elements(self, tree):
    for macro in tree.xpath('//macro', []):
      tree.remove(macro)


#------ ERRORS ------#
class InvalidConfigError(StandardError): pass 
class InvalidSchemaError(StandardError): pass

