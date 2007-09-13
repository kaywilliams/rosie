""" 
main.py

Python script defining the Build class, the primary controller for the
Distribution Management System (DiMS).
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '3.0'
__date__    = 'June 26th, 2007'

import imp
import sys

from rpmUtils.arch import getBaseArch

from dims import dispatch
from dims import pps
from dims import logger
from dims.configlib import ConfigError

from dims import sync
from dims.sync import cache
from dims.sync import link

from dimsbuild.callback  import BuildLogger, BuildSyncCallback, FilesCallback
from dimsbuild.constants import *
from dimsbuild.event     import Event

P = pps.Path # convenience

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

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
    
    # set up import_dirs
    import_dirs = [ P(x) for x in \
                         mainconfig.xpath('/dimsbuild/librarypaths/path/text()', [])
                       ]
    if options.libpath:
      import_dirs.insert(0, P(options.libpath)) # TODO make this a list
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(P(dir))
    
    # set up list of disabled modules
    disabled_modules = set()
    for k,v in eval_modlist(mainconfig.get('/dimsbuild/modules', None),
                            default=True).items():
      if v in BOOLEANS_FALSE: disabled_modules.add(k)
    
    disabled_modules.add('__init__') # hack, kinda; this isn't a module
    disabled_modules.add('lib') # +1; neither is this
    
    # update with distro-specific config
    for k,v in eval_modlist(distroconfig.get('/distro/main/modules', None),
                            default=True).items():
      if   v in BOOLEANS_FALSE: disabled_modules.add(k)
      elif v in BOOLEANS_TRUE:  disabled_modules.discard(k)
    
    # set up event superclass so that it contains good default values
    self.make_event_superclass(options, mainconfig, distroconfig)
    
    # clean up previous builds
    Event.logger.log(2, "Cleaning up previous builds")
    ##self.core.BUILD_DIR.rm(recursive=True, force=True)
    
    # load all enabled modules, register events, set up dispatcher
    loader = dispatch.Loader(
      top = Event(id='ALL', properties = dispatch.PROPERTY_META),
      api_ver = API_VERSION)
    loader.ignore = disabled_modules
    self.dispatch = dispatch.Dispatch(
                      loader.load(import_dirs, prefix='dimsbuild/modules')
                    )
    
    self.dispatch.pprint() #! debug statement for now
    self.dispatch.reset() #!
    ##sys.exit() #!
    
    # get everything started
    for e in self.dispatch: e._add_cli(parser)
    
    # raise init and other events prior
    self.dispatch.run(until='init')
  
  def apply_options(self, options):
    "Raise the 'applyopt' event, which plugins/modules can use to apply"
    "command-line argument configuration to themselves"
    # apply --clean to events
    for eventid in options.clean_events:
      e = self.dispatch.get(eventid)
      if e.test(dispatch.PROPERTY_PROTECTED):
        raise ValueError("Cannot --clean control-class event '%s'" % eventid)
      apply_flowcontrol(e, True)
    # apply --skip to events
    for eventid in options.skip_events:
      e = self.dispatch.get(eventid)
      if e.test(dispatch.PROPERTY_PROTECTED):
        raise ValueError("Cannot --skip control-class event '%s'" % eventid)
      apply_flowcontrol(e, False)
    
    # clear cache, if requested
    if options.clear_cache:
      self.log(0, "clearing cache")
      cache_dir = P(self.core.cache_handler.cache_dir)
      cache_dir.rm(recursive=True, force=True)
      cache_dir.mkdirs()
    
    # apply options:
    for e in self.dispatch: e._apply_options(options)
    
    # validate config
    for e in self.dispatch: e._validate()
  
  def main(self):
    "Build a distribution"
    self.dispatch.run(until=None)
  
  def get_mdlr_events(self):
    "Return a list of the modular events in this dimsbuild instance"
    return [ e.id for e in self.dispatch \
             if not e.test(dispatch.PROPERTY_PROTECTED) ]
  
  def make_event_superclass(self, options, mainconfig, distroconfig):
    """ 
    Set up a bunch of variables in the Event superclass that all subclasses
    inherit automatically.
    
    Accepts four parameters:
      options: an  OptionParser.Options  object  with  the  command  line
               arguments encountered during command line parsing
      mainconfig: the configlib.Config object created by parsing the main
               program   configuration   file,    normally   located   at
               '/etc/dimsbuild/dimsbuild.conf'
      distroconfig: the  configlib.Config  object created by parsing  the
               distribution-specific configuraiton file, normally located
               at '/etc/dimsbuild/<distro>/distro.conf'
    """
    # Event.cvars is a list of program 'control variables' - modules can use
    # this to communicate between themselves as necessary
    Event.cvars = CvarsDict()
    
    # set up loggers
    Event.logger    = BuildLogger(options.logthresh)
    Event.errlogger = logger.Logger(options.errthresh) # TODO - BuildLogger this #!
    
    # set up config dirs
    Event.mainconfig = mainconfig
    Event.config = distroconfig
    
    # set up base variables
    Event.cvars['base-vars'] = {}
    
    qstr = '/distro/main/%s/text()'
    base_vars = Event.cvars['base-vars']
    
    base_vars['product']  = Event.config.get(qstr % 'product')
    base_vars['version']  = Event.config.get(qstr % 'version')
    base_vars['release']  = Event.config.get(qstr % 'release', '0')
    base_vars['arch']     = Event.config.get(qstr % 'arch', 'i686')
    base_vars['basearch'] = getBaseArch(base_vars['arch'])
    base_vars['fullname'] = Event.config.get(qstr % 'fullname',
                            base_vars['product'])
    base_vars['webloc']   = Event.config.get(qstr % 'bug-url',
                            'No bug url provided')
    base_vars['pva']      = '%s-%s-%s' % (base_vars['product'],
                                          base_vars['version'],
                                          base_vars['basearch'])
    base_vars['product-path'] = base_vars['product']
    
    for k,v in base_vars.items():
      setattr(Event, k, v)
    
    # set up other directories
    Event.CACHE_DIR      = P(mainconfig.get('/dimsbuild/cache/path/text()',
                                           '/var/cache/dimsbuild'))
    Event.TEMP_DIR       = P('/tmp/dimsbuild')
    Event.BUILD_DIR      = Event.TEMP_DIR   / 'build'
    Event.DISTRO_DIR     = Event.BUILD_DIR  / base_vars['pva']
    Event.OUTPUT_DIR     = Event.DISTRO_DIR / 'output'
    Event.METADATA_DIR   = Event.DISTRO_DIR / 'builddata'
    Event.SOFTWARE_STORE = Event.OUTPUT_DIR / 'os'
    if options.sharepath:
      Event.SHARE_DIR = P(options.sharepath).abspath()
    else:
      Event.SHARE_DIR = P(mainconfig.get('/dimsbuild/sharepath/text()',
                                        '/usr/share/dimsbuild'))
    
    Event.CACHE_MAX_SIZE = int(mainconfig.get('/dimsbuild/cache/max-size/text()',
                                             30*1024**3))
    
    Event.cache_handler = cache.CachedSyncHandler(
                           cache_dir = Event.CACHE_DIR / '.cache',
                           cache_max_size = Event.CACHE_MAX_SIZE,
                          )
    Event.cache_callback = BuildSyncCallback(Event.logger)
    Event.copy_handler = sync.CopyHandler()
    Event.link_handler = link.LinkHandler()
    
    Event.files_callback = FilesCallback(Event.logger)


class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)


#------ UTILITY FUNCTIONS ------#
def load_module(path):
  "Load and return the module located at path"
  dir = path.dirname
  mod = path.basename.replace('.py', '')
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

def eval_modlist(mods, default=None):
  "Return a dictionary of modules and their enable status, as found in the"
  "config file"
  ret = {}
  
  if not mods: return ret
  
  mod_default = mods.get('@default', default)
  for mod in mods.getchildren():
    name = mod.get('text()')
    enabled = mod.get('@enabled', default).lower()
    if enabled == 'default':
      enabled = mod_default
    if enabled is None:
      raise ConfigError("Default status requested on '%s', but no default specified" % name)
    ret[name] = enabled
  
  return ret

def apply_flowcontrol(e, status):
  e._status = status
  
  # apply to all children if event has the PROPERTY_META property
  if e.test(dispatch.PROPERTY_META):
    for child in e.get_children():
      if not child.test(dispatch.PROPERTY_PROTECTED):
        apply_flowcontrol(child, status)
