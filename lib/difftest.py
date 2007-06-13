""" 
status.py

A flexible, modular status monitoring system for determining whether or not a
given set of data has changed or not.  Allows the client application to define
one or more 'handler' objects that examine some aspect of the system, program
state, or any other variable or condition to determine whether or not to execute
some other function.

For example, say a certain program wishes to track two input files as well as its
own output file.  It might define input and output handlers that check the file size
and modified times; if these both match, then the handler considers them unchanged.
Then, the program can tell by running status's Status.changed() function whether or
not it needs to regenerate its own output.

Handlers must implement the following interface:
  mdread(metadata): accepts a xmltree.XmlElement instance; responsible for setting
    up internal variables representing whatever was written out the last time
    mdwrite() was called.  If the handler doesn't need to read in metadata, this
    function can pass safely
  mdwrite(root): accepts a xmltree.XmlElement instance; responsible for encoding
    internal variables into xmltree.XmlElemnts that will be written to the mdfile.
    If the handler doesn't need to write out metadata, this function can pass
    safely.
  diff(): responsible for computing whether or not a change has taken place between
    the initial execution and the current one.  Returning an object with len >= 1
    will signify that a change has taken place, while returning a len 0 object means
    that no change has occurred.
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '1.0'
__date__    = 'June 12th, 2007'

import copy
import os

from os.path import join, exists

from dims import osutils
from dims import xmlserialize
from dims import xmltree

class DiffTest:
  """ 
  The main status manager class.  Contains a list of handlers, which are classes
  that actually perform the necessary checks.  Also capable of reading and writing
  a metadata file, stored in xml format, which can store information between sessions.
  """
  def __init__(self, mdfile):
    "mdfile is the location to use as the metadata file for storage between executions"
    self.mdfile = mdfile # the location of the file to store information
    
    self.handlers = [] # a list of registered handlers

  def addHandler(self, handler):
    "Add a handler that implements the status interface (described above)"
    self.handlers.append(handler)

  def read_metadata(self):
    "Read the file stored at self.mdfile and pass it to each of the handler's"
    "mdread() functions"
    try:
      metadata = xmltree.read(self.mdfile)
    except ValueError:
      return

    for handler in self.handlers:
      handler.mdread(metadata)

  def write_metadata(self):
    """ 
    Create an XmlTree from self.mdfile, if it exists, or make a new one and pass
    it to each of the handler's mdwrite() functions.  Due to the way xmltree.XmlTree's
    work, mdwrite() doesn't need to return any values; xmltree appends are destructive.
    """
    if exists(self.mdfile):
      md = xmltree.read(self.mdfile)
      root = md.getroot()
    else:
      root = xmltree.Element('metadata')
      md = xmltree.XmlTree(root)

    for handler in self.handlers:
      handler.mdwrite(root)

    md.write(self.mdfile)
  
  def changed(self):
    "Returns true if any handler returns a diff with length greater than 0"
    for handler in self.handlers:
      if len(handler.diff()) > 0:
        return True
    return False
  
  def test(self):
    "Perform a full check, from reading metadata to writing"
    self.read_metadata()
    change = self.changed()
    self.write_metadata()
    return change

def expand(list):
  "Expands a list of lists into a list"
  ret = []
  for item in list:
    if type(item) == type(list):
      ret.extend(item)
    else:
      ret.append(item)
  return ret

def diff(olddata, newdata):
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
      newfiles.extend(osutils.find(path, type=osutils.TYPE_FILE) + \
                      osutils.find(path, type=osutils.TYPE_LINK))
  newfiles.sort()
  
  oldfiles = olddata.keys() # list of files in metadata
  oldfiles.sort()
  
  # keep a list of already-processed elements so we don't add them in twice
  processed = []
  
  # first check for presence/absence of files in each list
  for x in newfiles:
    if x not in oldfiles:
      diffdict[x] = (None, DiffTuple(x))
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
  
def DiffTuple(file):
  "Generate a (size, mtime) tuple for file"
  try:
    stats = os.stat(file)
  except OSError:
    return (None, None)
  return (stats.st_size, stats.st_mtime)
  
class NewEntry:
  "Represents an item requested in a handler's data section that is not currently"
  "present in its metadata"""
class NoneEntry:
  "Represents an item requested in a handler's data section that does not exist"
  "for any reason"
  def __init__(self, index):
    "index is the path in the configuration object to this element"
    self.index = index
  def __eq__(self, other):
    try: return self.index == other.index
    except AttributeError: return False
  def __ne__(self, other):
    return not self == other
  def __str__(self):
    return "NoneEntry: %s" %(self.index,)


#------ HANDLERS ------#
class InputHandler:
  def __init__(self, data):
    self.data = expand(data)
    self.input = {}
    
  def mdread(self, metadata):
    for path in self.data:
      for file in metadata.xpath('/metadata/input/file'):
        self.input[file.get('@path')] = {'size':  int(file.get('size/text()')),
                                          'mtime': int(file.get('mtime/text()'))}
  
  def mdwrite(self, root):
    # remove previous node, if present
    try:
      root.remove(root.get('/metadata/input'))
    except TypeError:
      pass
    
    # create new parent node
    parent = xmltree.Element('input', parent=root)
    for path in self.data:
      for file in osutils.find(path, type=osutils.TYPE_FILE) + \
                  osutils.find(path, type=osutils.TYPE_LINK):
        e = xmltree.Element('file', parent=parent, attrs={'path': file})
        stat = os.stat(file)
        xmltree.Element('size',  parent=e, text=str(stat.st_size))
        xmltree.Element('mtime', parent=e, text=str(stat.st_mtime))
  
  def diff(self):
    return diff(self.input, self.data)

class OutputHandler:
  def __init__(self, data):
    self.data = expand(data)
    self.output = {}
    
  def mdread(self, metadata):
    for path in self.data:
      for file in metadata.xpath('/metadata/output/file'):
        self.output[file.get('@path')] = {'size':  int(file.get('size/text()')),
                                           'mtime': int(file.get('mtime/text()'))}
  
  def mdwrite(self, root):
    # remove previous node, if present
    try:
      root.remove(root.get('/metadata/output'))
    except TypeError:
      pass
    
    # create new parent node
    parent = xmltree.Element('output', parent=root)
    for path in self.data:
      for file in osutils.find(path, type=osutils.TYPE_FILE) + \
                  osutils.find(path, type=osutils.TYPE_LINK):
        e = xmltree.Element('file', parent=parent, attrs={'path': file})
        stat = os.stat(file)
        xmltree.Element('size',  parent=e, text=str(stat.st_size))
        xmltree.Element('mtime', parent=e, text=str(stat.st_mtime))
  
  def diff(self):
    return diff(self.output, self.data)

class ConfigHandler:
  def __init__(self, data, config):
    self.data = data
    self.config = config
    self.cfg = {}
    
  def mdread(self, metadata):
    for path in self.data:
      node = metadata.get('/metadata/config/value[@path="%s"]' % path, None)
      if node is not None:
        self.cfg[path] = node.xpath('elements/*', None) or \
                         node.xpath('text/text()', NoneEntry(path))
      else:
        self.cfg[path] = NewEntry()
  
  def mdwrite(self, root):
    # remove previous node, if present
    try:
      root.remove(root.get('/metadata/config'))
    except TypeError:
      pass
    
    config = xmltree.Element('config', parent=root)
    for path in self.data:
      value = xmltree.Element('value', parent=config, attrs={'path': path})
      for val in self.config.xpath(path, []):
        if type(val) == type(''): # a string
          xmltree.Element('text', parent=value, text=val)
        else:
          elements = xmltree.Element('elements', parent=value)
          elements.append(copy.copy(val).config) # append() is destructive
    
  def diff(self):
    diff = {}
    for path in self.data:
      if self.cfg.has_key(path):
        try:
          cfgval = self.config.xpath(path)
        except xmltree.XmlPathError:
          cfgval = NoneEntry(path)
        if self.cfg[path] != cfgval:
          diff[path] = (self.cfg[path], cfgval)
      else:
        try:
          cfgval = self.config.xpath(path)
        except xmltree.XmlPathError:
          cfgval = NoneEntry(path)
        diff[path] = (NewEntry(), cfgval)
    return diff

class VariablesHandler:
  def __init__(self, data, obj):
    self.data = data
    self.obj = obj
    
    self.vars = {}
  
  def mdread(self, metadata):
    for item in self.data:
      node = metadata.get('/metadata/variables/value[@variable="%s"]' % item)
      if node is None:
        self.vars[item] = NewEntry()
      else:
        if len(node.getchildren()) == 0:
          self.vars[item] = NoneEntry(item)
        else:
          self.vars[item] = xmlserialize.unserialize(node[0])
  
  def mdwrite(self, root):
    try:
      root.remove(root.get('/metadata/variables'))
    except TypeError:
      pass
    
    vars = xmltree.Element('variables', parent=root)
    for var in self.data:
      parent = xmltree.Element('value', parent=vars, attrs={'variable': var})
      try:
        val = eval('self.obj.%s' % var)
        parent.append(xmlserialize.serialize(val))
      except (AttributeError, TypeError):
        pass
  
  def diff(self):
    diff = {}
    for var in self.data:
      try:
        val = eval('self.obj.%s' % var)
      except AttributeError:
        val = NoneEntry(var)
      if self.vars.has_key(var):
        if self.vars[var] != val:
          diff[var] = (self.vars[var], val)
      else:
        diff[var] = (NewEntry(), val)
    return diff
