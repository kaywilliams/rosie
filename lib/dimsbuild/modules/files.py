""" 
files.py

Includes user-provided files and folders within the distribution folder.
"""

__author__  = 'Kay Williams <kwilliams@abodiosoftware.com>'
__version__ = '1.0'
__date__    = 'June 29th, 2007'

import os

from os.path      import join, exists, dirname, basename, isdir
from ConfigParser import ConfigParser

from dims import osutils
from dims import sync

from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from dimsbuild.interface import DiffMixin

API_VERSION = 4.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'files',
    'parent': 'MAIN',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  },
]

HOOK_MAPPING = {
  'FilesHook': 'files',
}

#------ HOOKS ------#
class FilesHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'files'
    
    self.interface = interface

    mdfile = join(self.interface.METADATA_DIR, 'files.md')

    self.DATA =  {
      'config':    ['/distro/files'],
      'input':     [],
      'output':    []
    }

    DiffMixin.__init__(self, mdfile, self.DATA)


  def setup(self):

    # Build up a dictionary of tuples keyed by full output path. Tuples contain 
    # * source-folder - resolved full path dirname of item specified in config or 
    #   locals
    # * sub-folder - path between source and item, empty unless folder expansion
    #   has occurred, useful during recursive sync operations to identify sync target
    # * file - filename, or empty if the item is a folder
    # * destination-folder - relative destination in the output folder as provided by a default
    #   value or specified by the dest element of the config file, used to compose
    #   output target folder

    self.files = {}
    for path in self.interface.config.xpath('/distro/files/path', []):

      # get destination folder
      try: 
        dest = path.attrib['dest']
        if dest == '/': dest = ''
      except KeyError: 
        dest = ''
  
      # resolve relative paths and expand folders to files
      items = self.interface.expand(path.text, resolve=True, prefix=None)
      items.sort()

      # deal with folders
      if len(items) > 1 :
        for item in items :
          source = item[:len(path.text)]
          common = item[len(path.text):]
          sub = dirname(common)
          base = basename(common)
          self.files[join(self.interface.SOFTWARE_STORE, dest, common)] = \
                    ((source, sub, base, dest))

      # deal with single files
      if len(items) == 1 :
        for item in items :
          common = basename(item)
          sub = dirname(common)
          base = basename(common)
          self.files[join(self.interface.SOFTWARE_STORE, dest, common)] = \
                    ((dirname(item), sub, base, dest)) 

    #print ('files: %s' % self.files)

    # create outfiles variable
    self.outfiles = []
    for item in self.files.values():
      source,sub,file,dest = item # common-path, source-folder, dest-folder
      self.outfiles.append(join(self.interface.SOFTWARE_STORE, dest, sub, file))

    self.addInput(self.files.keys())
    self.addOutput(self.outfiles)

    if self.files.keys() or self.handlers['output'].output.keys():
      self.interface.log(0, "processing user-provided files")

  def force(self):
    self.remove(self.handlers['output'].output.keys())
    self.clean_metadata()

  def check(self):
    return self.test_diffs()

  def run(self):

    removeset = set(self.handlers['output'].output.keys()).difference(set(self.outfiles))
    self.remove(removeset)

    addset = set(self.outfiles).difference(set(self.handlers['output'].output.keys()))
    self.add(addset)
 
    self.write_metadata()  
  
  def add(self, addset):
    if addset: 
      # convert set to list for sorting
      add = [item for item in addset]
      add.sort()
      self.interface.log(1, "adding files and folders '%d'" % len(add))  
      for item in add:
        source,sub,file,dest = self.files[item]
        full_dest = join(self.interface.SOFTWARE_STORE, dest)
        self.interface.log(2, "adding '%s'" % join(dest, sub, file))
        if item[-1] == "/":
          osutils.mkdir(item)
        else: 
         sync.sync(join(source,sub,file), join(full_dest, sub))

  def remove(self, removeset):

    if removeset:
	    self.interface.log(1, "removing files and folders '%d'" % len(removeset) )

    folders = []
    files = []

    for item in removeset:
      if item[-1] == '/': folders.append(item)
      else: files.append(item)        

    if files:
      for item in files:
        self.interface.log(2, "removing '%s'" % item[len(self.interface.SOFTWARE_STORE + '/'):])
        osutils.rm(item)

    remove = []
    for item in folders:
      if not osutils.find(item, type=0101): remove.append(item)

    if remove:
      for item in remove:
        self.interface.log(2, "removing '%s'" % item[len(self.interface.SOFTWARE_STORE + '/'):])
        osutils.rm(remove, force=True, recursive=True)
