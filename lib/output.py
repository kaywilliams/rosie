### THIS FILE IS DEPRECATED ###
### see difftest.py and interface.DiffMixin for replacement ###

""" 
output.py

An output interface template

This template  is intended for use with managing  the modification of  a single
file when both the input files and/or variables can and do change periodically.

OutputEventTemplate  defines  a  series of  functions that  allow for efficient
testing of both of these conditions, with appropriate behavior depending on the
results.

OutputEventMixin  is a mixin  for use with a  event.py interface that  executes
the functions defined in  OutputEventTemplate  in the  correct order.   Calling
the handle()  function on any  handler that implements  the OuputEventInterface
will result in correctly-handled output event processing.

OutputEventHandler   partially  implements  the  OutputEventTemplate,  using  a
metadata file to track  details about input and variables.   Classes interested
in utilizing this metadata format should subclass OutputEventHandler and define
the missing functions.

See  the  descriptions  in  the  OutputEventTemplate  as to  what  exactly each
function is responsible for doing.
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '1.5'
__date__    = 'March 8th, 2007'

import copy

from os.path import join, exists, isfile, isdir

from dims import listcompare
from dims import osutils
from dims import xmlserialize
from dims import xmltree

import magic
import os

#------ FUNCTIONS ------#
  
#---------- CLASSES ----------#
class OutputEventHandler:
  """ 
  OutputEventHandler   defines  several  of   the   functions   defined  in
  OutputEventTemplate that  have to do with metadata generation,  reading,
  and writing.  It utilizes an XML-based metadata file to store information
  about the  previous state of  the file it is associated  with in order to
  determine whether or not to execute modification code.
  
  In particular,  OutputEventHandler  defines  the  testInputChanged()  and
  storeMetadata()  functions.   It also  provides  several useful functions
  that subclasses can use when trying to implement testOutputChanged()  and
  potentially   testInputValid().     Subclasses   are   still   ultimately
  responsible for implementing all modification code.
  
  See the  individual function  documentation for more detailed information
  on what each function does.
  """
  def __init__(self, config, data, mdfile):
    """ 
    Initialize the OutputEventHandler
     * self.mdfile  : the metadata file in which modification metadata
                      is stored     
     * self.config  : the configuration file from which to read config
                      values     
     * self.data    : a data structure representing the output
                      object. Currently, four keys are supported:
                      'config' -- a list of xpath queries to elements
                      of the config file, 'variables' -- a list of
                      variables of the object, 'input' -- a list of
                      strings or lists to the input files, and 'output' --
                      a list of strings or lists to the output files/directories.
    """
    self.mdfile = mdfile
    self.config = config
    
    # data structure representing this output object
    self.data = data
    self._expand_data() # expand the lists in 'input' and 'output'
      
    # read in metadata - self.mdvalid is False unless read_metadata() finds a file
    self.mdvalid = False
    self.read_metadata()
    
    # set up control vars
    self.configvalid = False
    self.varsvalid   = False
    self.inputvalid  = False
    self.outputvalid = False
    
    # debug
    self.debug = False

  def expand_input(self, prefix=None):
    if self.data.has_key('input'):
      if prefix is None:
        prefix = osutils.dirname(self.config.file)
      self.data['input'] = map(lambda x: join(prefix, x), self.data['input'])

  def dprint(self, msg):
    "Print msg iff self.debug is True"
    if self.debug: print 'DEBUG: %s' % msg
  
  def read_metadata(self):
    """ 
    Read in self.mdfile and populate internal data structures:    

     * self.configvals : dictionary of configuration values keyed off
                         of their path in self.config                         
     * self.varvals    : dictionary of variable values    
     * self.input      : dictionary of input files with their last 
                         modified time and size as keys                        
     * self.output     : dictionary of output files with their last
                         modified time and size as keys
                         
    Above data structures are only populated if self.data[x][0] is
    true, where x is one of 'config', 'variables', 'input',
    'output'. Sets self.mdvalid once read is complete.    
    """
    try:
      metadata = xmltree.read(self.mdfile)
    except ValueError:
      return # self.mdvalid not set
    
    # reset values
    self.configvals = {}
    self.varvals    = {}
    self.input      = {}
    self.output     = {}
    
    # set up self.configvals dictionary
    for path in self.data.get('config', []):
      # if a path is listed twice, what happens? #!
      node = metadata.get('/metadata/config-values/value[@path="%s"]' % path, None)
      if node is not None:
        self.configvals[path] = node.xpath('elements/*', None) or \
                                node.xpath('text/text()', NoneEntry(path))
      else:
        self.configvals[path] = NewEntry()
    
    # set up self.varvals dictionary
    for item in self.data.get('variables', []):
      try:
        node = metadata.get('/metadata/variable-values/value[@variable="%s"]' % item)
        if len(node.getchildren()) == 0:
          self.varvals[item] = NoneEntry(item)
        else:
          self.varvals[item] = xmlserialize.unserialize(node[0])
      except xmltree.XmlPathError:
        self.varvals[item] = NewEntry()        

    # set up self.input and self.output. the input and output
    # elements have a similar structure, hence being lazy and
    # using a for-loop around it :).
    for key in ['input', 'output']:
      object = getattr(self, key)
      for source in metadata.xpath('/metadata/%s/file' % key):
        file = source.get('@path')
        object[file] = {'size': int(source.get('size').text),
                        'mtime': int(source.get('mtime').text)}
    self.mdvalid = True # md readin was successful
  
  def write_metadata(self):
    """ 
    Writes  metadata out to a file.   Converts the internal  data structures
    created in read_metadata(), above, into XML subtrees, assembles metadata
    tree  from  them,   and  writes  them  out  to  self.mdfile.    As  with 
    read_metadata(),  only  processes  the  elements  that  are  enabled  in
    self.data
    """
    if exists(self.mdfile):
      self.dprint("metadata file exists")
      root = xmltree.read(self.mdfile)
    else:
      self.dprint("metadata file doesn't exist")
      root = xmltree.Element('metadata')
    
    # set up <config-values> element
    if self.data.has_key('config'):
      if not (self.configvalid and self.mdvalid):
        try: root.remove(root.get('/metadata/config-values'))
        except TypeError: pass
        configvals = xmltree.Element('config-values')
        root.insert(0, configvals)
        for path in self.data['config']:
          value = xmltree.Element('value', parent=configvals, attrs={'path': path})
          for val in self.config.xpath(path, []):
            if type(val) == type(''): # config pointed to a string
              xmltree.Element('text', parent=value, text=val)
            else:
              elements = xmltree.Element('elements', parent=value)
              elements.append(copy.copy(val)) # append() is destructive, so copy
    
    # set up <variable-values> element
    if self.data.has_key('variables'):
      self.dprint("varsvalid? %s" % self.varsvalid)
      self.dprint("mdvalid? %s" % self.mdvalid)
      if not (self.varsvalid and self.mdvalid):
        self.dprint("inside the <variables> read section's if-block")
        try: root.remove(root.get('/metadata/variable-values'))
        except TypeError: pass
        varvals = xmltree.Element('variable-values')
        root.insert(1, varvals)
        for var in self.data['variables']:
          self.dprint("writing %s = %s to metadata file" % (var, eval('self.%s' % var)))
          parent = xmltree.Element('value', parent=varvals, attrs={'variable': var})
          parent.append(xmlserialize.serialize(eval('self.%s' % var)))
    
    # set up <input> and <output> elements. Watch me be lazy in the following
    # for-loop.
    for key in ['input', 'output']:
      valid = getattr(self, '%svalid' %(key,))
      if self.data.has_key(key):
        if not (valid and self.mdvalid):
          self.dprint("writing %s to metadata file" % key)
          try: root.remove(root.get('/metadata/%s' % key))
          except TypeError: pass          
          parent_node = xmltree.Element(key, parent=root)
          for path in self.data[key]:
            #self.dprint("path is %s" % path)
            for file in tree(path, type='f|l'):
              file_element = xmltree.Element('file', parent=parent_node, text=None,
                                             attrs={'path': file})
              stat = os.stat(file)
              size = xmltree.Element('size', parent=file_element, text=str(stat.st_size))
              mtime = xmltree.Element('mtime', parent=file_element, text=str(stat.st_mtime))
    root.write(self.mdfile)
  
  def test_input_changed(self):
    """ 
    Test to see if the input has changed.  Utilizes four  helper functions
    that  check  the three  different sections  of the metadata.   See the
    individual function descriptions for more information on the specifics
    of each test.
    """
    print 'default:test_input_changed()'
    if not self.mdvalid:
      return True
    else:
      # some not-ting going around because of the difference between
      # a file "changing" and a file being "valid"; they are opposites, at
      # least in this context.
      self.configvalid = (not self._test_configvals_changed())
      self.varsvalid   = (not self._test_vars_changed())
      self.inputvalid  = (not self._test_input_changed())
      self.outputvalid = (not self._test_output_changed())
      return not(self.configvalid and self.varsvalid and self.inputvalid and self.outputvalid)
  
  def _test_configvals_changed(self):
    """ 
    Check  config values to see  if  they have changed.   For each item in
    self.data['config'], get the value of the config element at that path.
    Then,  check self.configvals[item]  to see if they are equal.   If all
    elements  are  equal,  this test  succeeds;  if any  single element is
    different,  this  test  fails.   Additionally, if  self.data['config']
    contains an item not in self.configvals, this test fails.    
    """
    if not self.mdvalid: return True
    if not self.data.has_key('config'):
      return False
    else:
      for path in self.data['config']:
        if self.configvals.has_key(path):
          cfgval = self.config.xpath(path, [])
          if len(cfgval) == 0: cfgval = NoneEntry(path)
          if self.configvals[path] != cfgval:
            self.dprint("%s != %s" % (self.configvals[path], cfgval))
            return True
        else:
          #self.dprint("key = %s" % path)
          return True
    return False  
  
  test_config_changed = _test_configvals_changed
  
  def _test_vars_changed(self):
    if not self.mdvalid: return True
    if not self.data.has_key('variables'):
      return False
    else:
      for variable in self.data['variables']:
        if self.varvals.has_key(variable):
          try:
            varval = eval('self.%s' % variable)
          except AttributeError:
            varval = NoneEntry(variable)
          if self.varvals[variable] != varval:
            self.dprint("%s != %s" % (self.varvals[variable], varval))
            return True
        else:
          #self.dprint("key = %s" % path)
          return True
    return False
  
  test_vars_changed = _test_vars_changed
  
  def _test_input_changed(self):
    """ 
    Compare the input files' timestamp and size to see if any have
    changed. Use self.input as the list of elements to compare
    against.    
    """
    if not self.mdvalid: return True
    if not self.data.has_key('input'):
      return False
    # compare the files in the metadata with the files in self.data['input']
    d = self.diff(self.input, self.data['input'])
    if len(d) > 0:
      self.dprint('input: %s' %(d,))
    return self._has_changed(self.input, self.data['input'])
  
  def test_input_changed2(self):
    "Return a list of diff tuples of differeing input"
    if not self.mdvalid:
      return self.diff({}, self.data['input'])
    if not self.data.has_key('input'):
      return []
    return self.diff(self.input, self.data['input'])
  
  def _test_output_changed(self):
    """ 
    Compare the source's timestamp and size to the one stored in
    self.output; if they are the same, this test succeeds; else it
    fails.    
    """
    if not self.mdvalid: return True
    if not self.data.has_key('output'):
      return False
    # compare the files in the metadata with the files in self.data['output']
    d = self.diff(self.output, self.data['output'])
    if len(d) > 0:
      self.dprint('output: %s' %(d,))
    return self._has_changed(self.output, self.data['output'])
  
  def test_output_changed2(self):
    "Return a list of diff tuples of differing output"
    if not self.mdvalid:
      return self.diff({}, self.data['output'])
    if not self.data.has_key('output'):
      return []
    return self.diff(self.output, self.data['output'])

  def _has_changed(self, olddata, newdata):
    """ 
    Return True if the files in the metadata don't match the
    files in the new items list.
    """
    newfiles = []
    # newfiles is a list of files
    for item in newdata:
      if type(item) == str:
        item = [item]
      for path in item:
        newfiles.extend(tree(path, type='f|l'))
    oldfiles = olddata.keys()
    l, r, b = listcompare.compare(oldfiles, newfiles)
    if l: # obsolete files
      self.dprint("obsolete files found")
      return True
    if r: # new files
      self.dprint("new files found")
      return True
    if b:
      for f in b:
        try:
          stats = os.stat(f)
        except OSError:
          self.dprint("file '%s' not found" % f) # should never happen
          return True
        if (stats.st_mtime != olddata[f]['mtime']):
          self.dprint("file '%s' updated" % f)
          return True
        if (stats.st_size != olddata[f]['size']):
          self.dprint("file '%s' size differs" % f)
          return True
      #self.dprint("file '%s' unchanged" % f)
    return False
  
  def diff(self, olddata, newdata):
    """ 
    Return a dictionary of 'diff tuples' expressing the differences between
    olddata and newdata.  If there are no differences, the dictionary will be
    empty.  olddata is an expanded list of dictionaries containing 'size'
    and 'mtime' values; newdata is a list of lists of filenames.
    
    There are 3 possible types of diff tuples.  Each means something slightly
    different:
      (size, mtime):
        in metadata: file is present in metadata file
        in struct:   file is listed in struct and exists on disk
      (None, None):
        in metadata: N/A
        in struct:   file is listed in struct but doesn not exist on disk
      None:
        in metadata: file is not present in metadata file
        in struct:   file is not listed in struct
    """
    diffdict = {}
    
    newfiles = [] # list of files in the struct
    for item in newdata:
      if type(item) == str:
        item = [item]
      for path in item:
        newfiles.extend(tree(path, type='f|l'))
    newfiles.sort()
    
    oldfiles = olddata.keys() # list of files in metadata
    oldfiles.sort()
    
    # keep a list of already-processed elements so we don't add them in twice
    processed = []
    
    # first check for presence/absence of files in each list
    for x in newfiles:
      if x not in oldfiles:
        diffdict[x] = (None, self.__gen_diff_tuple2(x))
    for x in oldfiles:
      if x not in newfiles:
        processed.append(x)
        diffdict[x] = ((olddata[x]['size'], olddata[x]['mtime']), None)
    
    # now check sizes and mtimes
    for file in oldfiles:
      if file in processed: continue
      oldtup = (olddata[file]['size'], olddata[file]['mtime'])
      try:
        stats = os.stat(file)
        # files differ in size or mtime
        if (stats.st_mtime != olddata[file]['mtime']) or \
           (stats.st_size != olddata[file]['size']):
          diffdict[file] = (oldtup, (stats.st_size, stats.st_mtime))
      except OSError:
        # file does not exist
        diffdict[file] = (None, None)
    
    return diffdict
  
  def __gen_diff_tuple(self, file):
    "Generate a (filename, size, mtime) tuple"
    try:
      stats = os.stat(file)
    except OSError:
      return (file, None, None)
    return (file, stats.st_size, stats.st_mtime)
  
  def __gen_diff_tuple2(self, file):
    "Generate a (size, mtime) tuple for file"
    try:
      stats = os.stat(file)
    except OSError:
      return (None, None)
    return (stats.st_size, stats.st_mtime)
  
  def _expand_data(self):
    for key in ['input', 'output']:
      if self.data.has_key(key):
        newvalue = []
        for item in self.data[key]:
          if type(item) == list:
            newvalue.extend(item)
          else:
            newvalue.append(item)
        self.data[key] = newvalue

#--------- HELPER CLASSES ----------#
# In _test_configvals_changed(), above, there were a few cases we needed to
# test for.  Specifically, the watched config vals could change, or the config
# val could not exist in the config file.  These two classes were created to
# address this issue
class NewEntry:
  """ 
  NewEntry classes represent  when the watched configuration variables change;
  specifically,  when a configuration that  wasn't previously being tracked is
  added to the list of tracked variables.  Until the metadata has a record for
  this variable,  we need to include  a new entry for it,  represented by this
  class.
  """
class NoneEntry:
  """ 
  NoneEntry classes  represent when the output  class specifies that it wishes
  to  track a  configuration  option that is  not present in the  config file.
  NoneEntries have the special property that,  when compared to other entries,
  they  are equal to other  NoneEntries that have the same index  (config file
  path),  but different from all others.   This means that if  the config file
  doesn't have  a config entry for  two  executions  of  the  output  handler,
  _check_configvals_changed()  will  recognize  the  metadata  as  having  not
  changed.
  """
  def __init__(self, index):
    "index is the path in the configuration object to this element"
    self.index = index
  def __cmp__(self, other):
    "returns 0 if this Entry has the same index as other; 1 otherwise"
    try: return cmp(self.index, other.index)
    except AttributeError: return 1
  def __str__(self):
    return "NoneEntry: %s" %(self.index,)

#--------- EXCEPTIONS ----------#
class OutputInvalidError(StandardError):
  "Exception raised when the output is invalid."

class InputInvalidError(StandardError):
  "Exception raised when the input is invalid."
