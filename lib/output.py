""" 
output.py

An output interface template

This template  is intended for use with managing  the modification of  a single
file when both the input files and/or variables can and do change periodically.

OutputEventInterface  defines  a  series of functions that  allow for efficient
testing of both of these conditions, with appropriate behavior depending on the
results.

OutputEventMixin  is a mixin  for use with a  event.py interface that  executes
the functions defined in  OutputEventInterface in the  correct order.   Calling
the handle()  function on any  handler that implements  the OuputEventInterface
will result in correctly-handled output event processing.

OutputEventHandler  partially  implements  the  OutputEventInterface,  using  a
metadata file to track  details about input and variables.   Classes interested
in utilizing this metadata format should subclass OutputEventHandler and define
the missing functions.

See  the  descriptions  in  the  OutputEventInterface  as to  what exactly each
function is responsible for doing.
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "1.0"
__date__    = "March 8th, 2007"

from os.path import join, exists

import dims.md5lib as md5lib
import dims.osutils as osutils
import dims.xmltree as xmltree

import magic

class OutputEventInterface:
  """Interface for all output events.   Essentially  a java-style interface.
  Classes  that wish to use the output event API must subclass and implement
  this interface."""
  def __init__(self): pass
  
  def initVars(self):
    """ 
    Initialize any necessary variables.   This can include getting variables
    from an event.py interface, reading configuration, or any other variable
    setup method
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
  def testInputValid(self):
    """ 
    Check the input to ensure it is valid.  This may involve checking to make
    sure  the expected  files are present,  or that the  formats/contents  of
    these files is expected.
    
    If this test passes,  continue  with the modification in addOutput().  If
    this test fails, this is a fatal error usually.
    """
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

class OutputEventMixin:
  "Executes output events in order for classes that implement OutputEventInterface"
  def __init__(self): pass
  
  def pre(self, handler):
    handler.initVars()
    return not handler.testInputChanged() or not handler.testOutputValid()
    # testInputChanged() should be testInputValid()
  
  def modify(self, handler):
    "Perform the modification"
    handler.getInput()
    handler.testInputValid()
    handler.addOutput()
    handler.storeMetadata()
  
  def verifyType(self, file, type):
    return magic.match(file) == type

class OutputEventHandler(OutputEventInterface):
  """ 
  Partial implementation of OutputEventInterface
  
  OutputEventHandler   defines  several  of   the   functions   defined  in
  OutputEventInterface that  have to do with metadata generation,  reading,
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
  def __init__(self, config, data, file, mdfile=None):
    """ 
    Initialize the OutputEventHandler
     * self.file    : the file to be modified (the destination, not the source)
     * self.mdfile  : the metadata file in which modification metadata is stored
     * self.mddir   : dirname(self.mdfile)
     * self.config  : the configuration file from which to read config values
     * self.data    : a data structure representing the output object
    """
    self.file = file
    if mdfile is not None:
      self.mdfile = mdfile
    else:
      self.mdfile = join(osutils.dirname(file), '%s.md' % osutils.basename(file))
    self.mddir = osutils.dirname(self.mdfile)
    self.config = config
    
    # data structure representing this output object
    self.data = data
    
    # read in metadata - self.mdvalid is False unless read_metadata() finds a file
    self.mdvalid = False
    self.read_metadata()
    
    # set up control vars
    self.configvalid = False
    self.varsvalid   = False
    self.filesvalid  = False
    self.sourcevalid = False
  
  def read_metadata(self):
    """ 
    Read in self.mdfile and populate internal data structures:
     * self.configvals : dictionary of configuration values  keyed off of their
                         path in self.config
     * self.sourcemd5  : md5sum of the input file before modification
     * self.filemd5s   : list of (filename, md5sum) tuples
    Above data structures are only populated if self.data[x][0] is true,  where
    x is one of 'config', source', and 'file', respectively.  Sets self.mdvalid
    once read is complete.
    """
    try:
      metadata = xmltree.read(self.mdfile)
    except ValueError:
      return # self.mdvalid not set
    
    # reset values
    self.configvals = {}
    self.varvals = {}
    self.sourcemd5 = None
    self.filemd5s = []
    
    # set up self.configvals dictionary
    for item in self.data.get('config', []):
      try:
        node = metadata.get('/metadata/config-values/value[@path="%s"]' % item)[0]
        self.configvals[item] = node.text or NoneEntry(item)
      except IndexError:
        self.configvals[item] = NewEntry()
    
    # set up self.varvals dictionary
    for item in self.data.get('variables', []):
      try:
        node = metadata.get('/metadata/variable-values/value[@variable="%s"]' % item)[0]
        self.varvals[item] = node.text or NoneEntry(item)
      except IndexError:
        self.varvals[item] = NewEntry()
    
    # set up self.sourcemd5
    self.sourcemd5 = metadata.iget('/metadata/source-md5/text()', None)
    
    # set up self.filemd5s
    for c in metadata.get('/metadata/file-md5s/file'):
      self.filemd5s.append((c.attrib['name'], c.text))
    self.filemd5s.sort()
    
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
      md = xmltree.read(self.mdfile)
      root = md.getroot()
    else:
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
            xmltree.Element('value', parent=configvals, text=self.config.get(path),
                            attrs={'path': path})
          except xmltree.XmlPathError:
            xmltree.Element('value', parent=configvals, text=None, attrs={'path': path})
    
    # set up <variable-values> element
    if self.data.has_key('variables'):
      if not (self.varsvalid and self.mdvalid):
        try: root.remove(root.get('/metadata/variable-values', [])[0])
        except IndexError: pass
        varvals = xmltree.Element('variable-values')
        root.insert(1, varvals)
        for var in self.data['variables']:
          try:
            xmltree.Element('value', parent=varvals, text=eval('self.%s' % var),
                            attrs={'variable': var})
          except xmltree.XmlPathError:
            xmltree.Element('value', parent=varvals, text=None, attrs={'variable': var})
    
    # set up <source-md5> element
    if self.data.has_key('source'):
      if not (self.sourcevalid and self.mdvalid):
        try: root.remove(root.get('/metadata/source-md5', [])[0])
        except IndexError: pass
        sourcemd5 = xmltree.Element('source-md5', parent=root, text=md5lib.md5(self.file)[1],
                                    attrs={'name': self.file})
    
    # set up <file-md5s> element
    if self.data.has_key('files'):
      if not (self.filesvalid and self.mdvalid):
        try: root.remove(root.get('/metadata/file-md5s', [])[0])
        except IndexError: pass
        filemd5s = xmltree.Element('file-md5s', parent=root)
        try:
          curmd5s = md5lib.md5tree(self.config.get(self.data['files']))
        except (xmltree.XmlPathError, IndexError):
          curmd5s = []
        curmd5s.sort()
      
        for f, md5 in curmd5s:
          xmltree.Element('file', parent=filemd5s, text=md5, attrs={'name': f})
    
    md.write(self.mdfile)
  
  def testInputChanged(self):
    """ 
    Test to see if the input has changed.  Utilizes four  helper functions
    that  check  the three  different sections  of the metadata.   See the
    individual function descriptions for more information on the specifics
    of each test.
    """
    if not self.mdvalid:
      return False
    else:
      self.configvalid = self._test_configvals_changed()
      self.varsvalid   = self._test_vars_changed()
      self.filesvalid  = self._test_filemd5s_changed()
      self.sourcevalid = self._test_sourcemd5_changed()
      return self.configvalid and self.varsvalid and self.filesvalid and self.sourcevalid
  
  #def testOutputValid(self):
  #  pass
  
  def storeMetadata(self):
    "Simple wrapper to self.write_metadata()"
    self.write_metadata()
  
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
      return True
    else:
      for path in self.data['config']:
        if self.configvals.has_key(path):
          try:
            cfgval = self.config.get(path)
          except xmltree.XmlPathError:
            cfgval = NoneEntry(path)
          if self.configvals[path] != cfgval:
            #print "DEBUG:", self.configvals[path], "!=", cfgval
            return False
        else:
          #print 'key', path
          return False
    return True
  
  def _test_vars_changed(self):
    if not self.data.has_key('variables'):
      return True
    else:
      for variable in self.data['variables']:
        if self.varvals.has_key(variable):
          try:
            varval = eval('self.%s' % variable)
          except AttributeError:
            varval = NoneEntry(variable)
          if self.varvals[variable] != varval:
            #print "DEBUG:", self.varvals[variable], "!=", varval
            return False
        else:
          #print 'key', variable
          return False
    return True
  
  def _test_filemd5s_changed(self):
    """ 
    Test file md5s to see if any have changed.  Generates a filelist with md5sums
    on the folder specified in self.data['files'].  If the filelists are the same
    and all the md5sums match, this test succeeds; otherwise, it fails.
    """
    if not self.data.has_key('files'):
      return True
    else:
      try:
        curmd5s = md5lib.md5tree(self.config.get(self.data['files']))
      except (xmltree.XmlPathError, md5lib.Md5ReadError):
        curmd5s = []
      curmd5s.sort()
      return self.filemd5s == curmd5s
  
  def _test_sourcemd5_changed(self):
    """Compare the source md5sum to the one stored in self.sourcemd5; if they
    are the same, this test succeeds; otherwise, it fails."""
    if not self.data.has_key('source'):
      return True
    else:
      try:
        return md5lib.md5(self.file)[1] == self.sourcemd5
      except md5lib.Md5ReadError:
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
