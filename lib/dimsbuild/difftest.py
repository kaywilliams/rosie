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

from xml.sax import SAXParseException

import copy
import os
import time
import urllib2

from os.path import exists, join

from dims import osutils
from dims import spider
from dims import xmlserialize
from dims import xmltree


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
  "Return the (size,mtime) of a remote or local uri."
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
  
def diff(oldstats, newstats):
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
      in struct:   file is listed in struct but does not exist
    None:
      in metadata: file is not present in metadata file
      in struct:   file is not listed in struct
  """
  diffdict = {}

  # keep a list of already-processed elements so we don't add them in twice
  processed = []
  
  # first check for presence/absence of files in each list
  for x in newstats:
    if x not in oldstats:
      diffdict[x] = (None, newstats[x])
      processed.append(x)

  for x in oldstats:
    if x not in newstats:
      diffdict[x] = (oldstats[x], None)
      processed.append(x)
    
  # now check sizes and mtimes
  for file in oldstats:
    if file in processed: continue
    if oldstats[file] != newstats[file]:
      diffdict[file] = (oldstats[file], newstats[file])
  return diffdict
  
def expandPaths(paths):
  if type(paths) == str: paths = [paths]
  
  npaths = []
  for path in paths:
    npaths.extend(getFileList(path))

  return npaths

def getFileList(uri):
  "Return the files of a remote or local (absolute) uri"
  if uri.startswith('file:/'):
    uri = '/' + uri[6:].lstrip('/')
    
  if uri.startswith('/'): # local uri
    return osutils.find(uri, type=osutils.TYPE_FILE|osutils.TYPE_LINK)
  else: # remote uri
    return spider.find(uri, nregex='.*/$')
  
def DiffTuple(file):
  "Generate a (size, mtime) tuple for file"
  try:
    return getMetadata(file)
  except OSError, HTTPError:
    # FIXME: should the exception be raised here?
    return (None, None) 


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
    
    try:
      metadata = xmltree.read(self.mdfile)
    except (ValueError, IOError), SAXParseException:
      return

    handler.mdread(metadata)

  def clean_metadata(self):
    for handler in self.handlers:
      handler.clear()
    osutils.rm(self.mdfile, force=True)
      
  def read_metadata(self):
    """
    Read the file stored at self.mdfile and pass it to each of the
    handler's mdread() functions.
    """
    try: metadata = xmltree.read(self.mdfile)
    except ValueError: return

    for handler in self.handlers:
      handler.mdread(metadata)
    
  def write_metadata(self):
    """    
    Create an XmlTreeElement from self.mdfile, if it exists, or make a
    new one and pass it to each of the handler's mdwrite() functions.
    Due to the way xmltree.XmlTreeElements work, mdwrite() doesn't
    need to return any values; xmltree appends are destructive.    
    """
    if exists(self.mdfile): root = xmltree.read(self.mdfile)
    else: root = xmltree.Element('metadata')

    for handler in self.handlers:
      handler.mdwrite(root)

    root.write(self.mdfile)

  def changed(self, debug=None):
    "Returns true if any handler returns a diff with length greater than 0"
    old_dbgval = self.debug
    if debug is not None: self.debug = debug
    changed = False
    for handler in self.handlers:
      d = handler.diff()
      if len(d) > 0:
        changed = True
    self.debug = old_dbgval        
    return changed

  def test(self, debug=None):
    "Perform a full check, from reading metadata to writing"
    self.read_metadata()
    change = self.changed(debug=debug)
    self.write_metadata()
    return change

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
    return "NoneEntry: %s" % self.index

#------ HANDLERS ------#
class InputHandler:
  def __init__(self, data):
    self.name = 'input'
    self.data = []
    self.oldinput = {} # {file: stats}
    self.newinput = {} # {file: stats}

    self.filelists = {} # {path: expanded list}
    self.diffdict = {}  # {file: (old stats, new stats)}
    
    self.update(data)
        
  def update(self, data):
    if type(data) == str:
      self.data.append(data)
    else:
      for datum in data:
        if type(datum) == list:
          self.data.extend(datum)
        else:
          self.data.append(datum)
                                     
  def clear(self):
    self.oldinput.clear()
      
  def mdread(self, metadata):    
    for file in metadata.xpath('/metadata/input/file'):
      self.oldinput[file.get('@path')] = (int(file.get('size/text()')), int(file.get('mtime/text()')))
      
  def mdwrite(self, root):
    try: root.remove(root.get('input'))
    except TypeError: pass
    parent = xmltree.Element('input', parent=root)
    for datum in self.data:
      ifiles = self.filelists.get(datum, expandPaths(datum))
      for ifile in ifiles:
        size, mtime = self.newinput.get(ifile, DiffTuple(ifile))
        e = xmltree.Element('file', parent=parent, attrs={'path': ifile})
        xmltree.Element('size', parent=e, text=str(size))
        xmltree.Element('mtime', parent=e, text=str(mtime))
    
  def diff(self):
    for datum in self.data:
      if not self.filelists.has_key(datum):
        self.filelists[datum] = expandPaths(datum)
      ifiles = self.filelists[datum]
      for ifile in ifiles:
        self.newinput[ifile] = DiffTuple(ifile)        
    self.diffdict = diff(self.oldinput, self.newinput)    
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict

class OutputHandler:
  def __init__(self, data):
    self.name = 'output'
    
    self.data = []
    self.oldoutput = {}
    self.newoutput = {}
    
    self.diffdict = {}

    self.update(data)

  def update(self, data):
    if type(data) == str: data = [data]
    
    for datum in data:
      if type(datum) == list:
        self.data.extend(datum)
      else:
        self.data.append(datum)
    
  def clear(self):
    self.oldoutput.clear()
    
  def mdread(self, metadata):
    for file in metadata.xpath('/metadata/output/file'):
      self.oldoutput[file.get('@path')] = (int(file.get('size/text()')), int(file.get('mtime/text()')))
  
  def mdwrite(self, root):    
    try: root.remove(root.get('output'))
    except TypeError: pass
    
    parent = xmltree.uElement('output', parent=root)
    # write to metadata file
    paths = expandPaths(self.data)
    if paths:
      for output in paths:
        size, mtime = DiffTuple(output)
        e = xmltree.Element('file', parent=parent, attrs={'path': output})
        xmltree.Element('size', parent=e, text=str(size))
        xmltree.Element('mtime', parent=e, text=str(mtime))

  def diff(self):
    for file in expandPaths(self.data):
      self.newoutput[file] = DiffTuple(file)

    self.diffdict = diff(self.oldoutput, self.newoutput)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict

class ConfigHandler:
  def __init__(self, data, config):
    self.name = 'config'
    
    self.data = data
    self.config = config
    self.cfg = {}

    expand(self.data)

  def update(self, data):
    if type(data) == str: data = [data]

    for datum in data:
      if type(data) == list:
        self.data.extend(datum)
      else:
        self.data.append(datum)
      
  def clear(self):
    self.cfg.clear()
    
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
    self.diffdict = {}
    for path in self.data:
      if self.cfg.has_key(path):
        try:
          cfgval = self.config.xpath(path)
        except xmltree.XmlPathError:
          cfgval = NoneEntry(path)
        if self.cfg[path] != cfgval:
          self.diffdict[path] = (self.cfg[path], cfgval)
      else:
        try:
          cfgval = self.config.xpath(path)
        except xmltree.XmlPathError:
          cfgval = NoneEntry(path)
        self.diffdict[path] = (NewEntry(), cfgval)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict

class VariablesHandler:
  def __init__(self, data, obj):
    self.name = 'variables'
    
    self.data = data
    self.obj = obj
    self.vars = {}

    expand(self.data)

  def update(self, data):
    if type(data) == str: data = [data]

    for datum in data:
      if type(data) == list:
        self.data.extend(datum)
      else:
        self.data.append(datum)

  def clear(self):
    self.vars.clear()
    
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
    self.diffdict = {}
    for var in self.data:
      try:
        val = eval('self.obj.%s' % var)
        if val is None:
          val = NoneEntry(var)
      except AttributeError:
        val = NoneEntry(var)
      if self.vars.has_key(var):
        if self.vars[var] != val:
          self.diffdict[var] = (self.vars[var], val)
      else:
        self.diffdict[var] = (NewEntry(), val)
    if self.diffdict: self.dprint(self.diffdict)
    return self.diffdict
