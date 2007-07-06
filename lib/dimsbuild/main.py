""" 
main.py

Python script defining the Build class, the primary controller for the
Distribution Management System (DiMS).
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 26th, 2007'

import imp
import os
import sys

from os.path       import abspath, join, exists
from rpmUtils.arch import getBaseArch
from urlparse      import urlparse

from dims import logger
from dims import osutils
from dims.sortlib import dcompare

from dimsbuild import event
from dimsbuild import locals

from dimsbuild.callback  import BuildLogger
from dimsbuild.constants import *

# RPMS we need to check for
# createrepo
# anaconda-runtime

API_VERSION = 4.1

class Build:
  """ 
  Primary build class - framework upon which DiMS building is performed
  
  Build consists mostly of variable values  and a dispatch object,  which
  is responsible  for calling  module events  in order to perform various
  build tasks.  It also contains two loggers for printing out information
  to  the screen,  as well  as a  cache manager  for handling  caching of
  remote repository files.
  
  The  build  object  is  responsible for  loading  and initializing  all
  program  modules  and  plugins.   It  also  applies  configuration  and
  command-line arguments to its own internal variables as well as the its
  dispatcher.
  
  See dispatch.py  for more information on the role of the  dispatcher in
  the build process.
  """
  
  def __init__(self, options, parser, mainconfig, distroconfig):
    """ 
    Initialize a Build object
    
    Accepts four parameters:
      options: an  OptionParser.Options  object  with  the  command  line
               arguments encountered during command line parsing
      parser:  the OptionParser.OptionParser instance used to parse these
               command line arguments
      mainconfig: the configlib.Config object created by parsing the main
               program   configuration   file,    normally   located   at
               '/etc/dimsbuild/dimsbuild.conf'
      distroconfig: the  configlib.Config  object created by parsing  the
               distribution-specific configuraiton file, normally located
               at '/etc/dimsbuild/<distro>/distro.conf'
    
    These parameters are normally passed in from the command-line handler
    ('/usr/bin/dimsbuild')
    """
    # self.cvars is a list of program 'control variables' - modules can use
    # this to communicate between themselves as necessary
    self.cvars = CvarsDict()
    
    self.CACHE_DIR = '/var/cache/dimsbuild'
    self.TEMP_DIR  = '/tmp/dimsbuild'
    self.INPUT_STORE = join(self.CACHE_DIR, 'shared/repos')
    self.CACHE_MAX_SIZE = 30*1024**3 # 30 GB
    
    # set up loggers
    ##self.log = logger.Logger(options.logthresh)
    self.log = BuildLogger(options.logthresh)
    self.errlog = logger.Logger(options.errthresh)
    
    # set up config dirs
    self.mainconfig = mainconfig
    self.config = distroconfig
    
    # set up IMPORT_DIRS
    self.IMPORT_DIRS = mainconfig.xpath('//librarypaths/path/text()', [])
    if options.libpath:
      self.IMPORT_DIRS.insert(0, options.libpath) # TODO make this a list
    for dir in sys.path:
      if dir not in self.IMPORT_DIRS:
        self.IMPORT_DIRS.append(dir)
    
    if options.sharepath:
      self.sharepath = abspath(options.sharepath)
    else:
      self.sharepath = mainconfig.get('//sharepath/text()', None) or \
                       '/usr/share/dimsbuild'
    
    # set up base variables
    self.cvars['base-vars'] = {}
    self.cvars['base-vars']['product'] = self.config.get('//main/product/text()')
    self.cvars['base-vars']['version'] = self.config.get('//main/version/text()')
    self.cvars['base-vars']['release'] = self.config.get('//main/release/text()', '0')
    self.cvars['base-vars']['arch']    = self.config.get('//main/arch/text()', 'i686')
    self.cvars['base-vars']['basearch'] = getBaseArch(self.cvars['base-vars']['arch'])
    self.cvars['base-vars']['fullname'] = self.config.get('//main/fullname/text()',
                                                         self.cvars['base-vars']['product'])
    self.cvars['base-vars']['provider'] = self.config.get('//main/distro-provider/text()')
    self.cvars['base-vars']['webroot'] = self.config.get('/distro/main/publishpath/webroot/text()', 
                                                         '/var/www/html/')
    self.cvars['base-vars']['distrosroot'] = self.config.get('/distro/main/publishpath/distrosroot/text()',
                                                             'distros')
    self.cvars['base-vars']['pva'] = '%s-%s-%s' % (self.cvars['base-vars']['product'],
                                                   self.cvars['base-vars']['version'],
                                                   self.cvars['base-vars']['basearch'])
    self.cvars['base-vars']['productpath'] = self.cvars['base-vars']['product']
    
    # set up other directories
    self.DISTRO_DIR = join(self.CACHE_DIR, self.cvars['base-vars']['pva'])
    self.OUTPUT_DIR = join(self.DISTRO_DIR, 'output')
    self.METADATA_DIR = join(self.DISTRO_DIR, 'builddata')
    self.SOFTWARE_STORE = join(self.OUTPUT_DIR, 'os')    
    
    for dir in [self.SOFTWARE_STORE, self.METADATA_DIR, self.TEMP_DIR]:
      if not exists(dir):
        self.log(2, "Making directory '%s'" % dir)
      osutils.mkdir(dir, parent=True)
    
    # set up list of disabled modules
    self.disabled_modules = self.mainconfig.xpath('//modules/module[%s]/text()' % \
                            self.__generate_attr_bool('enabled', False), [])
    self.disabled_modules.append('__init__') # hack
    # update with distro-specific config
    for module in self.config.xpath('//modules/module', []):
      if module.attrib.get('enabled', 'False') in BOOLEANS_FALSE:
        if module.text not in self.disabled_modules:
          self.disabled_modules.append(module.text)
      else:
        if module.text in self.disabled_modules:
          self.disabled_modules.remove(modules.text)
    
    # self.userFC is a dictionary of user-specified flow control data keyed
    # by event id. Possible values are
    #  * None  - no user option specified
    #  * True  - force this event to run
    #  * False - prevent this event from running
    self.userFC = {}
    
    # load all enabled modules, register events, set up dispatcher
    self.__init_dispatch() # sets up self.dispatch
    
    self.dispatch.pprint() #!
    ##sys.exit() #!
    
    # get everything started - raise init and other events prior
    self.dispatch.get('init').interface.parser = parser
    self.dispatch.process(until='init')
  
  def __init_dispatch(self):
    """ 
    Initialize the dispatch object
    
    Loads  all  plugins  and  modules,  and then  registers them  with the
    dispatcher.   All plugins are disabled by default, and are only loaded
    if they are explicitly  enabled  (setting the  'enabled' attribute  to
    'true' in one  of the configuration files).   Conversely,  all modules
    are enabled by default,  and  are only  skipped if they  are explicity
    disabled  (again, by setting the 'enabled'  attribute to 'true' in the
    configuration file(s)).
    """
    self.dispatch = event.Dispatch()
    self.dispatch.disabled = self.disabled_modules
    self.dispatch.iargs.append(self)
    
    # load all enabled plugins
    enabled_plugins = self.mainconfig.xpath('//plugins/plugin[%s]/text()' % \
                        self.__generate_attr_bool('enabled', True), [])
    # update with distro-specific config
    for plugin in self.config.xpath('//plugins/plugin/text()', []):
      if plugin.attrib.get('enabled', 'True') in BOOLEANS_TRUE:
        if plugin.text not in enabled_plugins:
          enabled_plugins.append(plugin)
      else:
        if plugin.text in enabled_plugins:
          enabled_plugins.remove(plugin)
    
    for plugin in enabled_plugins:
      imported = False
      for path in self.IMPORT_DIRS:
        mod = join(path, 'dimsbuild/plugins', '%s.py' % plugin)
        if exists(mod):
          m = load_module(mod)
          self.dispatch.process_module(m)
          imported = True; break
      if not imported:
        raise ImportError, "Unable to load '%s' plugin; not found in any specified path" % plugin
    
    registered_modules = []
    for path in self.IMPORT_DIRS:
      modpath = join(path, 'dimsbuild/modules')
      if not exists(modpath): continue
      for mod in filter(None, osutils.find(modpath, nregex='.*\.pyc',
                                           prefix=False, maxdepth=1)):
        if mod.replace('.py', '') not in self.disabled_modules and \
           mod.replace('.py', '') not in registered_modules:
          m = load_module(join(modpath, mod))
          if m is None: continue # requested file wasn't a python module
          check_api_version(m) # raises ImportError
          self.dispatch.process_module(m)
          registered_modules.append(mod.replace('.py', ''))
    
    self.dispatch.commit()
  
  def __generate_attr_bool(self, attr, bool):
    "Generate an attr list that matches one of any acceptable booleans"
    if bool:
      return '@%s="True" or @%s="true" or @%s="Yes" or @%s="yes" or @%s="1"' % (attr, attr, attr, attr, attr)
    else:
      return '@%s="False" or @%s="false" or @%s="No" or @%s="no" or @%s="0"' % (attr, attr, attr, attr, attr)
  
  def preprocess(self):
    if exists(join(self.METADATA_DIR, '.firstrun')):
      # enable all events
      for e in self.dispatch:
        self.userFC[e.id] = True
    
  def apply_options(self, options):
    """Raise the 'applyopt' event, which plugins/modules can use to apply
    command-line argument configuration to themselves"""
    # point of failure - if the --force or --skip options change
    for e in options.force_events:
      self.__flowcontrol_apply(e, OPT_FORCE)
    for e in options.skip_events:
      self.__flowcontrol_apply(e, OPT_SKIP)
    
    self.dispatch.get('applyopt').interface.options = options
    self.dispatch.process(until='applyopt')
    
    for eventid, enabled in self.userFC.items():
      self.dispatch.get(eventid).status = enabled
      if enabled is None: continue
      if enabled: self.dispatch.force.append(eventid)
      else:       self.dispatch.skip.append(eventid)
    
  def __flowcontrol_apply(self, eventid, option=OPT_FORCE):
    "Internal function that applies the --force or --skip option to an event"
    e = self.dispatch.get(eventid, err=True)
    if e.test(event.PROP_CAN_DISABLE):
      self.userFC[eventid] = (option == OPT_FORCE)
      # apply to all successors if event has the PROP_META property
      if e.test(event.PROP_META):
        for child in e.get_children():
          if child.test(event.PROP_CAN_DISABLE):
            self.__flowcontrol_apply(child.id, option)
    else:
      raise ValueError, "Cannot %s control-class event '%s'" % (option, eventid)
  
  def get_mdlr_events(self):
    "Return a list of the modular events in this dimsbuild instance"
    list = []
    for e in self.dispatch:
      if e == -1: continue
      if e.test(event.PROP_CAN_DISABLE):
        list.append(e.id)
    return list
  
  def main(self):
    "Build a distribution"
    self.dispatch.process(until=None)
  
  def postprocess(self):
    osutils.rm(join(self.METADATA_DIR, '.firstrun'), force=True)
  
  def __compute_servers(self):
    "Compute a list of the servers represented in the configuration file"
    servers = []
    for path in self.config.xpath('//repos/*/repo/path/text()'):
      s,n,d,_,_,_ = urlparse(path)
      server = '://'.join((s,n))
      if server not in servers: servers.append(server)
    return servers

class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)

#------ UTILITY FUNCTIONS ------#
def load_module(path):
  "Load and return the module located at path"
  dir, mod = osutils.split(path)
  mod = mod.split('.py')[0] # remove .py
  try:
    fp, path, desc = imp.find_module(mod, [dir])
  except ImportError:
    return # this isn't a python module, thats ok
  try:
    module = imp.load_module(mod, fp, path, desc)
  except ImportError, e: # provide a more useful message
    raise ImportError, "Could not load module '%s':\n%s" % (path, e)
  fp and fp.close()
  return module

def check_api_version(module):
  """ 
  Examine the module m to ensure that the API it is expecting is provided
  by this Build instance.   A given API version  can support modules with
  the same major version number and any minor version number less than or
  equal to its own.   Thus, for example,  a main.py with API_VERSION  set
  to 3.4 results in the following behavior:
    * 0.0-2.x is rejected
    * 3.0-3.4 is accepted
    * 3.5-X.x is rejected
  where X and x are any positive integers.
  """
  if not hasattr(module, 'API_VERSION'):
    raise ImportError, "Module '%s' does not have API_VERSION variable" % module.__file__
  mAPI = str(module.API_VERSION)
  rAPI = str(API_VERSION)
  
  reqM, reqm = rAPI.split('.')
  reqM = '%s.0' % reqM
  if dcompare(mAPI, rAPI) > 0:
    raise ImportError, "Module API version '%s' is greater than the supplied API version '%s' in module %s" % (rAPI, mAPI, module.__file__)
  elif dcompare(mAPI, rAPI) <= 0 and dcompare (mAPI, reqM) >= 0:
    pass
  elif dcompare(mAPI, rAPI) < 0:
    raise ImportError, "Module API version '%s' is less than the required API version '%s' in module %s" % (mAPI, rAPI, module.__file__)
  else:
    print "DEBUG: mAPI =", mAPI, "rAPI = ", rAPI
