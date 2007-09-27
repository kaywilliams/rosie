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
from dims.configlib import ConfigError

from dims import sync
from dims.sync import cache
from dims.sync import link

from dimsbuild.callback  import BuildSyncCallback, FilesCallback
from dimsbuild.constants import *
from dimsbuild.event     import Event
from dimsbuild.logging   import BuildLogger, L0, L1, L2
from dimsbuild.validate  import (ConfigValidator, MainConfigValidator,
                                 InvalidConfigError, InvalidSchemaError)

P = pps.Path # convenience, same is used throughout most modules

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

class Build(object):
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
    import_dirs = self._compute_import_dirs(mainconfig, options)
    
    # set up list of disabled modules
    disabled_modules = self._compute_disabled_modules(mainconfig, distroconfig, options)
    
    # set up event superclass so that it contains good default values
    self._seed_event_defaults(options, mainconfig, distroconfig)
    
    # load all enabled modules, register events, set up dispatcher
    loader = dispatch.Loader(top = AllEvent(), api_ver = API_VERSION)
    loader.ignore = disabled_modules
    try:
      self.dispatch = dispatch.Dispatch(
                        loader.load(import_dirs, prefix='dimsbuild/modules')
                      )
    except ImportError, e:
      Event.errlogger.log(0, L0("Error loading core dimsbuild file: %s" % e))
      sys.exit(1)
    
    # allow events to add their command-line options to the parser
    for e in self.dispatch: e._add_cli(parser)
    
  def apply_options(self, options):
    "Allow events to apply option results to themselves"
    # apply --force to events
    for eventid in options.force_events:
      e = self.dispatch.get(eventid)
      if e.test(dispatch.PROPERTY_PROTECTED):
        Event.errlogger.log(0, L0("Cannot --force protected event '%s'" % eventid))
        sys.exit(1)
      e.status = True
    # apply --skip to events
    for eventid in options.skip_events:
      e = self.dispatch.get(eventid)
      if e.test(dispatch.PROPERTY_PROTECTED):
        Event.errlogger.log(0, L0("Cannot --skip protected event '%s'" % eventid))
        sys.exit(1)
      e.status = False
    
    # clear cache, if requested
    if options.clear_cache:
      Event.logger.log(0, L0("clearing cache"))
      cache_dir = P(self.core.cache_handler.cache_dir)
      cache_dir.rm(recursive=True, force=True)
      cache_dir.mkdirs()
    
    # list events, if requested
    if options.list_events:
      self.dispatch.pprint()
      sys.exit()
    
    # perform validation, if not specified otherwise
    if not options.no_validate:
      try:
        self._validate_configs()
      except InvalidSchemaError, e:
        Event.errlogger.log(0, L0("Schema file used in validation appears to be invalid"))
        Event.errlogger.log(0, L0(e))
        sys.exit(1)
      except InvalidConfigError, e:
        Event.errlogger.log(0, L0("Config file validation against given schema failed"))
        Event.errlogger.log(0, L0(e))
        sys.exit(1)
      except Exception, e:
        Event.errlogger.log(0, L0("Unhandled exception: %s" % e))
        sys.exit(1)
      if options.validate_only:
        sys.exit()
    
    # apply options to individual events
    for e in self.dispatch: e._apply_options(options)
  
  def main(self):
    "Build a distribution"
    self.dispatch.execute(until=None)
  
  def _compute_import_dirs(self, mainconfig, options):
    "Compute a list of directories to try importing from"
    import_dirs = [ P(x) for x in \
      mainconfig.xpath('/dimsbuild/librarypaths/path/text()', []) ]
    
    if options.libpath:
      import_dirs.insert(0, P(options.libpath)) # TODO make this a list
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(P(dir))
    
    return import_dirs
  
  def _compute_disabled_modules(self, mainconfig, distroconfig, options):
    "Compute a list of modules dimsbuild should not load"
    disabled_modules = set()
    disabled_modules.update(options.disabled_modules)
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
    
    return disabled_modules
  
  def _validate_configs(self):
    Event.logger.log(0, L0("validating config"))
    
    Event.logger.log(1, L1("dimsbuild.conf"))
    Event.mcvalidator.validate('/dimsbuild', schemafile='dimsbuild.rng')
    
    Event.logger.log(1, L1(P(Event.config.file).basename))
    # validate individual sections of distro.conf
    Event.validator.validate('/distro/main', schemafile='main.rng')    
    for e in self.dispatch:
      e.validate()
    # validate top-level elements
    Event.validator.validateElements()
  
  def _seed_event_defaults(self, options, mainconfig, distroconfig):
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
    Event.errlogger = BuildLogger(options.errthresh)
    
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
    Event.METADATA_DIR    = Event.CACHE_DIR  / base_vars['pva']
    
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
    
    Event.files_callback = FilesCallback(Event.logger, Event.METADATA_DIR)
    
    Event.mcvalidator = MainConfigValidator(Event.SHARE_DIR/'schemas',
                                            Event.mainconfig.file)
    Event.validator = ConfigValidator(Event.SHARE_DIR/'schemas/distro.conf',
                                      Event.config.file, Event.errlogger)


class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)


class AllEvent(Event):
  "Top level event that is the ancestor of all other events.  Changing this "  
  "event's version will cause all events to automatically run."
  def __init__(self):
    Event.__init__(self,
      id = 'ALL',
      version = 0,
      properties = dispatch.PROPERTY_META,
    )


#------ UTILITY FUNCTIONS ------#
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
