""" 
output.py

An output interface template

This template  is intended for use with managing  the modification of  a single
file when both the input files and/or variables can and do change periodically.

OutputEventTemplate  defines  a  series of functions that  allow for efficient
testing of both of these conditions, with appropriate behavior depending on the
results.

OutputEventMixin  is a mixin  for use with a  event.py interface that  executes
the functions defined in  OutputEventTemplate in the  correct order.   Calling
the handle()  function on any  handler that implements  the OuputEventInterface
will result in correctly-handled output event processing.

OutputEventHandler  partially  implements  the  OutputEventTemplate,  using  a
metadata file to track  details about input and variables.   Classes interested
in utilizing this metadata format should subclass OutputEventHandler and define
the missing functions.

See  the  descriptions  in  the  OutputEventTemplate  as to  what exactly each
function is responsible for doing.
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "1.0"
__date__    = "March 8th, 2007"

from os.path import join, exists, isfile, isdir

import dims.md5lib  as md5lib
import dims.xmltree as xmltree
import dims.mkrpm   as mkrpm
import dims.osutils as osutils

import magic
import os

#--------- FUNCTIONS --------------#
def tree(path, type='d|f|l', prefix=True):
  types = type.split('|')
  rtn = []
  if 'd' in types:
    rtn.extend(osutils.find(location=path, name='*', type=osutils.TYPE_DIR, prefix=prefix))
  if 'f' in types:
    rtn.extend(osutils.find(location=path, name='*', type=osutils.TYPE_FILE, prefix=prefix))
  if 'l' in types:
    rtn.extend(osutils.find(location=path, name='*', type=osutils.TYPE_LINK, prefix=prefix))
  return rtn
  
#------------ TEMPLATES -------------#
class OutputEventTemplate:
  """
  Interface for all output events.   Essentially  a java-style interface.
  Classes  that wish to use the output event API must subclass and implement
  this interface.
  """
  def __init__(self): pass
  
  def initVars(self):
    """ 
    Initialize any necessary variables.   This can include getting variables
    from an event.py interface, reading configuration, or any other variable
    setup method
    """
    raise NotImplementedError
  def testInputValid(self):
    """ 
    Check the input to ensure it is valid.  This may involve checking to make
    sure  the expected  files are present,  or that the  formats/contents  of
    these files is expected.
    
    If this test passes,  continue  with the modification in addOutput().  If
    this test fails, this is a fatal error usually.
    """
    raise NotImplementedError
  def testInputChanged(self):
    """ 
    Test to see if the input file(s) have changed in some way.   This may be
    accomplished by checking against a saved md5 sum or comparing filelists,
    for example.
    
    If  this test  passes,  then  the  file(s)  associated  with  the  class
    implementing  this  interface will be  modified.   If it fails,  then it
    continues to check if the output files are valid (checkOutputValid())
    """
    raise NotImplementedError
  def testOutputValid(self):
    """ 
    Test to see if output  file(s) are valid.   This  may be a format check;
    for example,  testing to see if an output image is in ext2 format, or it
    may be a simple examination to ensure it contains what is expected.
    
    If this test passes, then the output doesn't need to be modified and the
    implementing classes modify function may return.   If it fails, continue
    with getInput()
    """
    raise NotImplementedError
  def removeObsoletes(self):
    "Remove obsolete files from the input"
    raise NotImplementedError
  def removeInvalids(self):
    "Remove invalid files from the output"
    raise NotImplementedError
  def getInput(self):
    "Get input files from one or more sources"
    raise NotImplementedError
  def addOutput(self):
    """ 
    Take files from the input and move them to the output, possibly modifying
    them in the process.
    """
    raise NotImplementedError
  def storeMetadata(self):
    """ 
    Store  any  necessary  metadata  so  that  subsequent  executions  of the
    implementing  class  can  run  testInputChanged()  and testOutputValid().
    This may involve  storing filelists,  md5sums,  timestamps,  or any other
    file metadata information.   The format of this metadata is not mandated;
    the client class should use whatever is easiest for it to process.
    """
    raise NotImplementedError

#---------- MIXINS ----------#
class OutputEventMixin:
  "Executes output events in order for classes that implement OutputEventTemplate"
  def __init__(self): pass
  
  def pre(self, handler):
    handler.initVars()
    if handler.testInputChanged():
      #print "DEBUG: input changed"
      handler.removeObsoletes()
      return True
    if not handler.testOutputValid():
      #print "DEBUG: output invalid"
      handler.removeInvalids()
      return True
    #print "DEBUG: input unchanged, output valid"
    return False
  
  def modify(self, handler):
    "Perform the modification"
    if not handler.testInputValid():
      raise InputInvalidException, "the input files are invalid"
    handler.getInput()
    handler.addOutput()
    if not handler.testOutputValid():
      raise OutputInvalidException, "the output files are invalid"      
    handler.storeMetadata()
  
  def verifyType(self, file, type):
    return magic.match(file) == type

#---------- CLASSES ----------#
class OutputEventHandler(OutputEventTemplate):
  """ 
  Partial implementation of OutputEventTemplate
  
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
  def __init__(self, config, data, file, mdfile=None, mddir=None):
    """ 
    Initialize the OutputEventHandler
    
     * self.file    : the file to be modified (the destination, not the
                      source)     
     * self.mdfile  : the metadata file in which modification metadata
                      is stored     
     * self.mddir   : dirname(self.mdfile) if not specified. If not
                      None, it should be the file that contains the
                      output files' location. For example, the
                      LogosHandler sets mddir to be builddata/logos.                      
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
    self.file = file
    self.mdfile = mdfile or join(osutils.dirname(file), '%s.md' % osutils.basename(file))
    self.mddir = mddir or osutils.dirname(self.mdfile)
    self.config = config
    
    # data structure representing this output object
    self.data = data
    
    # read in metadata - self.mdvalid is False unless read_metadata() finds a file
    self.mdvalid = False
    self.read_metadata()
    
    # set up control vars
    self.configvalid = False
    self.varsvalid   = False
    self.inputvalid  = False
    self.outputvalid = False
  
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
    self.varvals = {}
    self.input = {}
    self.output = {}
    
    # set up self.configvals dictionary
    for item in self.data.get('config', []):
      try:
        node = metadata.get('/metadata/config-values/value[@path="%s"]/*' %(item,))[0]
        self.configvals[item] = node or NoneEntry(item)
      except IndexError:
        try:
          node = metadata.get('/metadata/config-values/value[@path="%s"]' %(item,))[0]
          self.configvals[item] = node.text or NoneEntry(item)          
        except IndexError:
          self.configvals[item] = NewEntry()

    # set up self.varvals dictionary
    for item in self.data.get('variables', []):
      try:
        node = metadata.get('/metadata/variable-values/value[@variable="%s"]/text()' %(item,))[0]
        self.varvals[item] = node or NoneEntry(item)
      except IndexError:
        self.varvals[item] = NewEntry()        

    # set up self.input and self.output. the input and output
    # elements have a similar structure, hence being lazy and
    # using a for-loop around it :).
    for key in ['input', 'output']:
      object = getattr(self, key)
      if self.data.has_key(key):
        for item in self.data[key]:
          if type(item) == str:
            item = [item]
          for path in item:            
            for file in tree(path, type='f|l'):            
              source = metadata.iget('/metadata/%s/file[@path="%s"]' %(key, file,), None)
              if source:
                object[file] = {}
                object[file]['size'] = int(source.iget('size').text)
                object[file]['mtime'] = int(source.iget('lastModified').text)
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
      #print "DEBUG: the metadata file exists"
      md = xmltree.read(self.mdfile)
      root = md.getroot()
    else:
      #print "DEBUG: the metadata file doesn't exist"
      root = xmltree.Element('metadata')
      md = xmltree.XmlTree(root)
    
    # set up <config-values> element
    if self.data.has_key('config'):
      if not (self.configvalid and self.mdvalid):
        try: root.remove(root.get('/metadata/config-values', [])[0])
        except IndexError: pass
        configvals = xmltree.Element('config-values')
        root.insert(0, configvals)
        for path in self.data['config']:
          try:
            xmltree.Element('value', parent=configvals, text=self.config.get(path).__str__(),
                            attrs={'path': path})
          except xmltree.XmlPathError:
            xmltree.Element('value', parent=configvals, text=None, attrs={'path': path})
    
    # set up <variable-values> element
    if self.data.has_key('variables'):
      #print "DEBUG: varsvalid?", self.varsvalid
      #print "DEBUG: mdvalid?", self.mdvalid
      if not (self.varsvalid and self.mdvalid):
        #print "DEBUG: inside the <variables> read section's if-block"
        try: root.remove(root.get('/metadata/variable-values', [])[0])
        except IndexError: pass
        varvals = xmltree.Element('variable-values')
        root.insert(1, varvals)
        for var in self.data['variables']:
          try:            
            #print "DEBUG: writing %s = %s to metadata file" %(var, eval('self.%s' %(var,)))
            xmltree.Element('value', parent=varvals, text=eval('self.%s' % var),
                            attrs={'variable': var})
          except xmltree.XmlPathError:
            xmltree.Element('value', parent=varvals, text=None, attrs={'variable': var})

    # set up <input> and <output> elements. Watch me be lazy in the following
    # for-loop.
    for key in ['input', 'output']:
      valid = getattr(self, '%svalid' %(key,))
      if self.data.has_key(key):
        if not (valid and self.mdvalid):
          #print "DEBUG: writing %s to metadata file" %(key,)
          try: root.remove(root.get('/metadata/%s' %(key,), [])[0])
          except IndexError: pass          
          parent_node = xmltree.Element(key, parent=root)
          for item in self.data[key]:
            if type(item) == str:
              item = [item]
            for path in item:
              #print "DEBUG: path is %s" %(path,)            
              if isfile(path):
                files = [path]
              else:
                files = tree(path, type='f|l')
              for file in files:
                file_element = xmltree.Element('file', parent=parent_node, text=None,
                                               attrs={'path': file})
                stat = os.stat(file)
                size = xmltree.Element('size', parent=file_element, text=str(stat.st_size))
                mtime = xmltree.Element('lastModified', parent=file_element, text=str(stat.st_mtime))
    md.write(self.mdfile)

  def initVars(self): pass

  def removeObsoletes(self): pass

  def removeInvalids(self): pass

  def getInput(self): pass

  def addOutput(self): pass
    
  def testInputChanged(self):
    """ 
    Test to see if the input has changed.  Utilizes four  helper functions
    that  check  the three  different sections  of the metadata.   See the
    individual function descriptions for more information on the specifics
    of each test.
    """
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
  
  def storeMetadata(self):
    "Simple wrapper to self.write_metadata()"
    self.write_metadata()

  def testInputValid(self):
    return True

  def testOutputValid(self):
    return True
  
  def _test_configvals_changed(self):
    """ 
    Check  config values to see  if  they have changed.   For each item in
    self.data['config'], get the value of the config element at that path.
    Then,  check self.configvals[item]  to see if they are equal.   If all
    elements  are  equal,  this test  succeeds;  if any  single element is
    different,  this  test  fails.   Additionally, if  self.data['config']
    contains an item not in self.configvals, this test fails.    
    """
    if not self.data.has_key('config'):
      return False
    else:
      for path in self.data['config']:
        if self.configvals.has_key(path):
          try:
            cfgval = self.config.get(path)
          except xmltree.XmlPathError:
            cfgval = NoneEntry(path)
          if self.configvals[path] != cfgval:
            #print "DEBUG: ", self.configvals[path], "!=", cfgval
            return True
        else:
          #print "DEBUG: key=%s" %(path,)
          return True
    return False  

  def _test_vars_changed(self):
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
            #print "DEBUG:", self.varvals[variable], "!=", varval
            return True
        else:
          #print "DEBUG: key=%s" %(path,)
          return True
    return False
  
  def _test_input_changed(self):
    """
    Compare the input files' timestamp and size to see if any have
    changed. Use self.input as the list of elements to compare
    against.    
    """
    if not self.data.has_key('input'):
      return False
    # compare the files in the metadata with the files in self.data['input']
    return self._has_changed(self.input, self.data['input'])
  
  def _test_output_changed(self):
    """
    Compare the source's timestamp and size to the one stored in
    self.output; if they are the same, this test succeeds else it
    fails.    
    """
    if not self.data.has_key('output'):
      return False
    # compare the files in the metadata with the files in self.data['output']
    return self._has_changed(self.output, self.data['output'])

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
        if isfile(path):
          newfiles.append(path)
        else:
          newfiles.extend(tree(path, type='f|l'))
    oldfiles = olddata.keys()
    newfiles.sort()
    oldfiles.sort()
    if newfiles != oldfiles:
      #print "DEBUG: old files obsolete"
      return True
    for file in oldfiles:
      try:
        stats = os.stat(file)
      except OSError:
        #print "DEBUG: file %s wasn't found" %(file,)
        return True # file has been deleted, or wasn't found.
                    # Either way something bad happened.
      if (stats.st_mtime != olddata[file]['mtime']) or \
             (stats.st_size  != olddata[file]['size']):
        #print "DEBUG: file %s is invalid" %(file,)
        return True # invalid file
      #print "DEBUG: file '%s' has not changed" %(file,)
    return False

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
class OutputInvalidException(StandardError):
  "Exception raised when the output is invalid."

class InputInvalidException(StandardError):
  "Exception raised when the input is invalid."
