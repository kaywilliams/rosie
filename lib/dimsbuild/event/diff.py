from dims import difftest

class DiffMixin:
  def __init__(self):
    self._diff_tester = difftest.DiffTest(self.mdfile)
    self._diff_handlers = {}
    self._diff_set = {}
  
  def clean(self):
    self.clean_metadata()
  
  def check(self):
    return self.test_diffs()
  
  # former DiffMixin stuff
  def setup_diff(self, data):
    if data.has_key('input'):
      self._add_handler(difftest.InputHandler(data['input']))
    if data.has_key('output'):
      self._add_handler(difftest.OutputHandler(data['output']))
    if data.has_key('variables'):
      self._add_handler(difftest.VariablesHandler(data['variables'], self))
    if data.has_key('config'):
      self._add_handler(difftest.ConfigHandler(data['config'], self.config))
  
  def _add_handler(self, handler):
    self._diff_tester.addHandler(handler)
    self._diff_handlers[handler.name] = handler
  
  def clean_metadata(self):  self._diff_tester.clean_metadata()
  def read_metadata(self):   self._diff_tester.read_metadata()
  def write_metadata(self):  self._diff_tester.write_metadata()
  
  def test_diffs(self, debug=None):
    old_dbgval = self._diff_tester.debug
    if debug is not None:
      self._diff_tester.debug = debug
    
    for handler in self._diff_handlers.values():
      self._diff_set[handler.name] = (len(handler.diff()) > 0)
    
    self._diff_tester.debug = old_dbgval
    
    if len(self._diff_set) > 0:
      return (True in self._diff_set.values())
    else:
      return True
  
  def has_changed(self, name, err=False):
    if not self._diff_handlers.has_key(name):
      if err:
        raise RuntimeError("Missing %s metadata handler" % name)
      return False
    if not self._diff_set.has_key(name):
      self._diff_set[name] = (len(self._diff_handlers[name].diff()) > 0)
    return self._diff_set[name]
  
  def var_changed_from_value(self, var, value):
    if not self._diff_handlers['variables']:
      raise RuntimeError("No 'variables' metadata handler")
    if self._diff_handlers['variables'].diffdict.has_key(var) and \
       self._diff_handlers['variables'].vars.has_key(var) and \
       self._diff_handlers['variables'].vars[var] == value:
      return True
    else:
      return False
