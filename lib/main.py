""" 
main.py

Python script defining the Build class, the primary controller for the
Distribution Management System (DiMS).
"""

__author__  = "Daniel Musgrave <dmusgrave@abodiosoftware.com>"
__version__ = "3.0"
__date__    = "March 7th, 2007"

import imp
import os
import sys

from os.path       import join, exists
from rpmUtils.arch import getBaseArch
from urlparse      import urlparse

import dims.logger  as logger
import dims.osutils as osutils

from dims.CacheManager import CacheManager
from dims.sortlib      import dcompare
from dims.xmltree      import XmlPathError

import event
import locals

from interface import EventInterface
from callback  import BuildLogger

# RPMS we need to check for
# createrepo
# anaconda-runtime
# expect

BOOLEANS_TRUE  = ['True', 'true', 'Yes', 'yes', '1']
BOOLEANS_FALSE = ['False', 'false', 'No', 'no', '0']
OPT_FORCE = '--force'
OPT_SKIP  = '--skip'

API_VERSION = 3.0

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
    self.CACHE = '/var/cache/dimsbuild/'
    self.INPUT_STORE = join(self.CACHE, 'shared/stores')
    self.TEMP = '/tmp/dimsbuild'
    self.CACHE_MAX_SIZE = 30*1024**3 # 30 GB
    
    # set up loggers
    ##self.log = logger.Logger(options.logthresh)
    self.log = BuildLogger(options.logthresh)
    self.errlog = logger.Logger(options.errthresh)
    
    # set up config dirs
    self.mainconfig = mainconfig
    self.config = distroconfig
    self.CONFIG_DIR = osutils.dirname(self.config.file)
    
    self.COMPS_FILE = None
    
    # set up IMPORT_DIRS
    self.IMPORT_DIRS = mainconfig.mget('//librarypaths/path/text()')
    if options.libpath: self.IMPORT_DIRS.insert(0, options.libpath) # TODO make this a list
    for dir in sys.path:
      if dir not in self.IMPORT_DIRS: self.IMPORT_DIRS.append(dir)


    self.sharepath = options.sharepath or \
                     mainconfig.get('//sharepath/text()', None) or \
                     '/usr/share/dimsbuild'
    
    # set up base variables
    self.base_vars = {}
    self.base_vars['product'] = self.config.get('//main/product/text()')
    self.base_vars['version'] = self.config.get('//main/version/text()')
    self.base_vars['release'] = self.config.get('//main/release/text()', '0')
    self.base_vars['arch']    = self.config.get('//main/arch/text()', 'i686')
    self.base_vars['basearch'] = getBaseArch(self.base_vars['arch'])
    self.base_vars['fullname'] = self.config.get('//main/fullname/text()',
                                                 self.base_vars['product'])
    self.base_vars['provider'] = self.config.get('//main/distro-provider/text()')
    
    # set up other directories
    distro_prefix = 'distros/%s/%s/%s' % (self.base_vars['product'],
                                          self.base_vars['version'],
                                          self.base_vars['basearch'])
    self.SOFTWARE_STORE = join(self.CACHE, distro_prefix, 'os')
    self.METADATA = join(self.CACHE, distro_prefix, 'builddata')

    self.PUBLISH_DIR = join(self.config.get('//main/webroot/text()', '/var/www/html'),
                            self.config.get('//main/publishpath/text()', 'open_software'),
                            self.base_vars['product'])
    
    self.cachemanager = CacheManager(self.__compute_servers(),
                                     self.INPUT_STORE,
                                     self.CACHE_MAX_SIZE)
    
    for dir in [self.SOFTWARE_STORE, self.METADATA, self.TEMP]:
      self.log(2, "Making directory '%s'" % dir)
      osutils.mkdir(dir, parent=True)
    
    # load all modules, register events, set up dispatcher
    self.__init_dispatch() # sets up self.dispatch
    
    # self.mvars is a place that modules/plugins can store various var values
    # that they themselves or other modules/plugins can access
    self.mvars = {}
    # self.userFC is a dictionary of user-specified flow control data keyed
    # by event id. Possible values are
    #  * None  - no user option specified
    #  * True  - force this event to run
    #  * False - prevent this event from running
    self.userFC = {}
    
    # get everything started - raise init - this is so hack
    self.dispatch.next()
    self.dispatch.raise_event(self) # raise preALL
    self.dispatch.move(2) # skip ALL (meta event)
    self.dispatch.raise_event(self, parser) # raise init
    self.dispatch.next()
    
  
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
    
    # load all enabled plugins
    enabled_plugins = self.mainconfig.mget('//plugins/plugin[%s]/text()' % \
                        self.__generate_attr_bool('enabled', True), [])
    # update with distro-specific config
    for plugin in self.config.mget('//plugins/plugin/text()', []):
      if plugin.attrib.get('enabled', 'True') in BOOLEANS_TRUE:
        if plugin.text not in enabled_plugins:
          enabled_plugins.append(plugin)
      else:
        if plugin.text in enabled_plugins:
          enabled_plugins.remove(plugin)
    
    for plugin in enabled_plugins:
      imported = False
      for path in self.IMPORT_DIRS:
        mod = join(path, 'plugins', '%s.py' % plugin)
        if exists(mod):
          m = load_module(mod)
          self.dispatch.process_module(m)
          imported = True; break
      if not imported:
        raise ImportError, "Unable to load '%s' plugin; not found in any specified path" % plugin
    
    # load all modules not disabled in config
    disabled_modules = self.mainconfig.mget('//modules/module[%s]/text()' % \
                         self.__generate_attr_bool('enabled', False), [])
    disabled_modules.append('__init__') # hack
    # update with distro-specific config
    for module in self.config.mget('//modules/module/text()', []):
      if module.attrib.get('enabled', 'False') in BOOLEANS_FALSE:
        if module.text not in disabled_modules:
          disabled_plugins.append(module)
      else:
        if module.text in disabled_modules:
          disabled_modules.remove(modules)
    registered_modules = []
    
    for path in self.IMPORT_DIRS:
      modpath = join(path, 'modules')
      if not exists(modpath): continue
      for mod in filter(None, osutils.find(modpath, nregex='.*\.pyc',
                                           prefix=False, maxdepth=1)):
        if mod.replace('.py', '') not in disabled_modules and \
           mod.replace('.py', '') not in registered_modules:
          m = load_module(join(modpath, mod))
          if m is None: continue # requested file wasn't a python module
          self.__check_api_version(m) # raises ImportError
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
    if exists(join(self.METADATA, '.firstrun')):
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
    
    self.dispatch.raise_event(self, options) # raise applyopt - kinda hackish
    self.dispatch.next() # advance to next event
    
    for eventid, enabled in self.userFC.items():
      if enabled is None: continue
      if enabled: self.dispatch.force.append(eventid)
      else:       self.dispatch.skip.append(eventid)
  
  def __flowcontrol_apply(self, eventid, option=OPT_FORCE):
    "Internal function that applies the --force or --skip option to an event"
    e = self.dispatch.get(eventid, err=True)
    if e.test(event.PROP_CAN_DISABLE):
      self.userFC[eventid] = (option == OPT_FORCE)
      # apply to immediate children if a meta event
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
      if e.test(event.PROP_CAN_DISABLE):
        list.append(e.id)
    return list
  
  def main(self):
    "Build a distribution"
    self.dispatch.process(self)
  
  def postprocess(self):
    osutils.rm(join(self.METADATA, '.firstrun'), force=True)
  
  def __compute_servers(self):
    "Compute a list of the servers represented in the configuration file"
    servers = []
    for path in self.config.emget('//stores/*/store/path/text()'):
      s,n,d,_,_,_ = urlparse(path)
      server = '://'.join((s,n))
      if server not in servers: servers.append(server)
    return servers
  
  def __check_api_version(self, module):
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
      raise ImportError, "Module '%s' does not have API_VERSION variable" % module
    mAPI = str(module.API_VERSION)
    rAPI = str(API_VERSION)
    
    reqM, reqm = rAPI.split('.')
    reqM = '%s.0' % reqM
    if dcompare(mAPI, rAPI) > 0:
      raise ImportError, "Module API version '%s' is greater than the supplied API version '%s'" % (rAPI, mAPI)
    elif dcompare(mAPI, rAPI) <= 0 and dcompare (mAPI, reqM) >= 0:
      pass
    elif dcompare(mAPI, rAPI) < 0:
      raise ImportError, "Module API version '%s' is less than the required API version '%s'" % (mAPI, rAPI)
    else:
      print "DEBUG: mAPI =", mAPI, "rAPI = ", rAPI


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
