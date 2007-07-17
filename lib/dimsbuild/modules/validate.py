from lxml    import etree
from os.path import exists, join

import copy
import os

import dims.filereader as filereader
import dims.xmltree    as xmltree

from dimsbuild.event     import HookExit, EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'validate',
    'conditional-requires': ['applyopt', 'clean'],
    'properties': EVENT_TYPE_MDLR,
    'parent': 'ALL',
    'interface': 'ValidateInterface',
  },    
]

HOOK_MAPPING = {
  'ApplyOptHook': 'applyopt',
  'InitHook':     'init',
  'ValidateHook': 'validate',
}

#------------ INTERFACES ------------#
class ValidateInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
    self.schemaspath = join(base.sharepath, 'schemas')
  
  def validate(self, xquery, schemafile=None, schemacontents=None, what='distro'):
    if what != self.cvars.get('validate', 'distro'): return
    
    if (schemafile is None and schemacontents is None) or \
           (schemafile is not None and schemacontents is not None):
      raise RuntimeError("either the schema file or the schema contents should be specified")
    
    cwd = os.getcwd()
    os.chdir(join(self.schemaspath, 'distro.conf'))
    try:
      schemacontents = schemacontents or self.getSchema(schemafile)
      try:
        schema = etree.RelaxNG(etree.ElementTree(etree.fromstring(schemacontents)))
      except etree.RelaxNGParseError, e:
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
            % (self.cvarcs.get('validate', 'distro'), schemafile, why))
        else:
          self.raiseInvalidConfig("validation of the %s.conf failed: %s" \
            % (self.cvars.get('validate', 'distro', why)))
    finally:
      os.chdir(cwd)
  
  def raiseInvalidConfig(self, message):
    raise InvalidConfigError(message)
  
  def getSchema(self, filename):
    if self.cvars.get('validate', 'distro') == 'dimsbuild':
      schema = join(self.schemaspath, filename)
    else:      
      schema = join(self.schemaspath, 'distro.conf', filename)
      
    if exists(schema):
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


#---------- HOOKS ------------#
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'validate.init'
    self.interface = interface
  
  def run(self):
    parser = self.interface.getOptParser('validate')
    parser.add_option('--valid',
                      default=None,
                      dest='validate',
                      metavar='[distro|dimsbuild]',
                      help="validates the distro.conf or dimsbuild.conf and exits",
                      choices=['distro', 'dimsbuild'])


class ApplyOptHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'validate.applyopt'
    self.interface = interface
  
  def run(self):
    if self.interface.options.validate is not None:
      self.interface.cvars['exit-after-validate'] = True
      self.interface.cvars['validate'] = self.interface.options.validate
      

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'validate.validate'
    self.interface = interface
  
  def setup(self):
    self.interface.log(0, "performing config validation")
    if self.interface.cvars.get('validate', 'distro') == 'distro':
      self.interface.log(1, "validating distro.conf")
    else:
      self.interface.log(1, "validating dimsbuild.conf")
    
  def run(self):
    if self.interface.cvars.get('validate', 'distro') == 'distro':
      self.interface.validate('/distro/main', schemafile='main.rng', what='distro')
    else:
      self.interface.validate('/dimsbuild', schemafile='dimsbuild.rng', what='dimsbuild')
  
  def post(self):
    if self.interface.cvars.get('exit-after-validate', False):
      self.interface.log(4, "exiting because the '--valid' option was used at command line")
      raise HookExit

class InvalidConfigError(StandardError): pass 
class InvalidSchemaError(StandardError): pass
