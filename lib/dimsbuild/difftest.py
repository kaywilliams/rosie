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
import time
import urllib2

from os.path import join, exists

from dims import osutils
from dims import spider
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
    
    self.debug = False
  
  def dprint(self, msg):
    if self.debug: print msg

  def addHandler(self, handler):
    "Add a handler that implements the status interface (described above)"
    handler.debug = self.debug
    handler.dprint = self.dprint
    self.handlers.append(handler)
    expand(handler.data)
    
    try:
      metadata = xmltree.read(self.mdfile)
    except ValueError:
      return

    handler.mdread(metadata)

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
    Create an XmlTreeElement from self.mdfile, if it exists, or make a new one and
    pass it to each of the handler's mdwrite() functions.  Due to the way
    xmltree.XmlTreeElements work, mdwrite() doesn't need to return any values;
    xmltree appends are destructive.
    """
    if exists(self.mdfile):
      root = xmltree.read(self.mdfile)
    else:
      root = xmltree.Element('metadata')

    for handler in self.handlers:
      handler.mdwrite(root)

    root.write(self.mdfile)
  
  def changed(self):
    "Returns true if any handler returns a diff with length greater than 0"
    changed = False
    for handler in self.handlers:
      d = handler.diff()
      if len(d) > 0:
        changed = True
        self.dprint(d)
    return changed
  
  def test(self):
    "Perform a full check, from reading metadata to writing"
    self.read_metadata()
    change = self.changed()
    self.write_metadata()
    return change

def expand(list):
  "Expands a list of lists into a list, in place."
  old = []
  new = []
  # expand all lists in the list
  for item in list:
    if type(item) == type(list):
      new.extend(item)
      old.append(item)    
  for x in old: list.remove(x)
  for x in new: list.append(x)

def getMetadata(uri):
  "Return the (size,mtime) of a remote of local uri"
  if uri.startswith('file:/'):
    uri = '/' + uri[6:].lstrip('/')

  if uri.startswith('/'): # local uri
    stats = os.stat(uri)
    return (stats.st_size, stats.st_mtime)
  else: # remote uri
    request = urllib2.Request(uri)
    request.get_method = lambda : 'HEAD'
    http_file = urllib2.urlopen(request)
    headers = http_file.info()
    size = headers.getheader('content-length') or '0'
    mtime = headers.getheader('last-modified') or 'Wed, 31 Dec 1969 16:00:00 GMT'
    http_file.close()
    return int(size), int(time.mktime(time.strptime(mtime, '%a, %d %b %Y %H:%M:%S GMT')))

def getFiles(uri):
  "Return the files of a remote of local uri"
  if uri.startswith('file:/'):
    uri = '/' + uri[6:].lstrip('/')

  if uri.startswith('/'): # local uri
    files = osutils.find(uri) or [uri]
  else: # remote uri
    files = spider.find(uri)
  return files
  
def diff(olddata, newfiles):
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
      in struct:   file is listed in struct but does not exist on disk
    None:
      in metadata: file is not present in metadata file
      in struct:   file is not listed in struct
  """
  diffdict = {}
  
  oldfiles = olddata.keys() # list of files in metadata

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
      size, mtime = getMetadata(file)
      # files differ in size or mtime
      if (mtime != olddata[file]['mtime']) or \
         (size != olddata[file]['size']):
        diffdict[file] = (oldtup, (size, mtime))
    except OSError, HTTPError:
      # file does not exist
      diffdict[file] = (None, None)
  
  return diffdict
  
def DiffTuple(file):
  "Generate a (size, mtime) tuple for file"
  try:
    return getMetadata(file)
  except OSError, HTTPError:
    # FIXME: should the exception be raised here?
    return (None, None) 
  
class NewEntry:
  "Represents an item requested in a handler's data section that is not currently"
  "present in its metadata"
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
    self.data = data
    self.input = {}
    self.diffdict = {}

  def mdread(self, metadata):
    for file in metadata.xpath('/metadata/input/file'):
      self.input[file.get('@path')] = {'size':  int(file.get('size/text()')),
                                       'mtime': int(file.get('mtime/text()'))}
      
  def mdwrite(self, root):
    try: root.remove(root.get('input'))
    except TypeError: pass
    
    parent = xmltree.Element('input', parent=root)
    for datum in self.data:
      size, mtime = (None, None)
      if datum in self.diffdict.keys():
        size, mtime = self.diffdict[datum][1]

      if size is None or mtime is None:
        # should not happen, unless the input handler's data was
        # modified after diff() was called.        
        size, mtime = getMetadata(datum)
          
      e = xmltree.Element('file', parent=parent, attrs={'path': datum})
      xmltree.Element('size', parent=e, text=str(size))
      xmltree.Element('mtime', parent=e, text=str(mtime))
    
  def diff(self):
    self.diffdict = diff(self.input, self.data)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict

class OutputHandler:
  def __init__(self, data):
    self.data = data
    self.output = {}
    
  def mdread(self, metadata):
    for file in metadata.xpath('/metadata/output/file'):
      self.output[file.get('@path')] = {'size':  int(file.get('size/text()')),
                                        'mtime': int(file.get('mtime/text()'))}
  
  def mdwrite(self, root):
    try: root.remove('output')
    except TypeError: pass
    parent = xmltree.uElement('output', parent=root)
    for datum in self.data:
      # it is OK to call getFiles() because all the files in self.data
      # are local files, and it is guaranteed that no spidering will
      # take place. We have to call getFiles() because there might be
      # new files added to self.data between test_diffs() and
      # now.
      for file in getFiles(datum):
        size, mtime = getMetadata(file) 
        
        e = xmltree.Element('file', parent=parent, attrs={'path': file})
        xmltree.Element('size', parent=e, text=str(size))
        xmltree.Element('mtime', parent=e, text=str(mtime))

  def diff(self):    
    ### CHANGE. June 2, 2007: changed the second parameter in the
    ### diff() function call to be self.output.keys(); it was
    ### self.data before.    
    d = diff(self.output, self.output.keys())
    if d: self.dprint(d)
    return d

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
          elements.append(copy.copy(val)) # append() is destructive
    
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
    if diff: self.dprint(diff)
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
    if diff: self.dprint(diff)
    return diff
