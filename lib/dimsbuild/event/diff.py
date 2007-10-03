from dims import difftest

class DiffMixin:
  def __init__(self):
    self.diff = DiffObject(self)
  
  def clean(self):
    self.diff.clean_metadata()
  
  def check(self):
    return self.diff.test_diffs()


class DiffObject:
  "Dummy object to contain diff-related functions"
  def __init__(self, ptr):
    self.ptr = ptr
    self.tester = difftest.DiffTest(self.ptr.mdfile)
    self.handlers = {}
    self.diff_set = {}
  
  # former DiffMixin stuff
  def setup(self, data):
    if data.has_key('input'):
      self.add_handler(difftest.InputHandler(data['input']))
    if data.has_key('output'):
      self.add_handler(difftest.OutputHandler(data['output']))
    if data.has_key('variables'):
      self.add_handler(difftest.VariablesHandler(data['variables'], self.ptr))
    if data.has_key('config'):
      self.add_handler(difftest.ConfigHandler(data['config'], self.ptr.config))
  
  def add_handler(self, handler):
    self.tester.addHandler(handler)
    self.handlers[handler.name] = handler
  
  def clean_metadata(self):  self.tester.clean_metadata()
  def read_metadata(self):   self.tester.read_metadata()
  def write_metadata(self):  self.tester.write_metadata()
  
  def test_diffs(self, debug=None):
    old_dbgval = self.tester.debug
    if debug is not None:
      self.tester.debug = debug
    
    for handler in self.handlers.values():
      self.diff_set[handler.name] = (len(handler.diff()) > 0)
    
    self.tester.debug = old_dbgval
    
    if len(self.diff_set) > 0:
      return (True in self.diff_set.values())
    else:
      return True
  
  def has_changed(self, name, err=False):
    if not self.handlers.has_key(name):
      if err:
        raise RuntimeError("Missing %s metadata handler" % name)
      return False
    return self.diff_set.setdefault(name, len(self.handlers[name].diff()) > 0)
