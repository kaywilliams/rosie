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
import time

from rpmUtils.arch import getBaseArch

from dims import dispatch
from dims import pps
from dims import xmllib

from dims import sync
from dims.sync import cache
from dims.sync import link

from dimsbuild.callback  import BuildSyncCallback, FilesCallback
from dimsbuild.constants import *
from dimsbuild.event     import Event
from dimsbuild.logging   import make_log, L0, L1, L2
from dimsbuild.validate  import (ConfigValidator, MainConfigValidator,
                                 InvalidConfigError, InvalidSchemaError)

from dimsbuild.event.loader import Loader

P = pps.Path # convenience, same is used throughout most modules

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

DEBUG = True # enable to print tracebacks; disable for 'release mode'

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
    
    # set up lists of enabled and disabled modules
    enabled, disabled = self._compute_modules(distroconfig, options)
    
    # set up event superclass so that it contains good default values
    self._seed_event_defaults(options, mainconfig, distroconfig)
    
    # load all enabled modules, register events, set up dispatcher
    loader = Loader(top = AllEvent(), api_ver = API_VERSION,
                    enabled = enabled, disabled = disabled)
    
    try:
      self.dispatch = dispatch.Dispatch(
                        loader.load(import_dirs, prefix='dimsbuild/modules')
                      )
      self.disabled_modules = loader.disabled
      self.enabled_modules = loader.enabled
    except ImportError, e:
      Event.logger.log(0, L0("Error loading core dimsbuild files: %s" % e))
      if DEBUG: raise
      sys.exit(1)
    
    # allow events to add their command-line options to the parser
    for e in self.dispatch: e._add_cli(parser)
    
  def apply_options(self, options):
    "Allow events to apply option results to themselves"
    # apply --force to events
    for eventid in options.force_events:
      e = self.dispatch.get(eventid)
      if e.test(dispatch.PROPERTY_PROTECTED):
        Event.logger.log(0, L0("Cannot --force protected event '%s'" % eventid))
        sys.exit(1)
      e.status = True
    # apply --skip to events
    for eventid in options.skip_events:
      e = self.dispatch.get(eventid)
      if e.test(dispatch.PROPERTY_PROTECTED):
        Event.logger.log(0, L0("Cannot --skip protected event '%s'" % eventid))
        sys.exit(1)
      e.status = False
    
    # clear cache, if requested
    if options.clear_cache:
      Event.logger.log(0, L0("clearing cache"))
      Event.cache_handler.cache_dir.rm(recursive=True, force=True)
      Event.cache_handler.cache_dir.mkdirs()
    
    # list events, if requested
    if options.list_events:
      self.dispatch.pprint()
      sys.exit()

    # perform validation, if not specified otherwise
    if not options.no_validate:
      try:
        self._validate_configs()
      except InvalidSchemaError, e:
        Event.logger.log(0, L0("Schema file used in validation appears to be invalid"))
        Event.logger.log(0, L0(e))
        sys.exit(1)
      except InvalidConfigError, e:
        Event.logger.log(0, L0("Config file validation against given schema failed"))
        Event.logger.log(0, L0(e))
        sys.exit(1)
      except Exception, e:
        Event.logger.log(0, L0("Unhandled exception: %s" % e))
        if DEBUG: raise
        sys.exit(1)
      if options.validate_only:
        sys.exit()
    
    # apply options to individual events
    for e in self.dispatch: e._apply_options(options)
  
  def main(self):
    "Build a distribution"
    self._log_header()
    self.dispatch.execute(until=None)
    self._log_footer()
  
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
  
  def _compute_modules(self, distroconfig, options):
    "Compute a list of modules dimsbuild should not load"
    enabled  = set(options.enabled_modules)
    disabled = set(options.disabled_modules)
    
    for module in distroconfig.xpath('/distro/*'):
      if module.tag == 'main': continue
      if module.get('@enabled', 'True') in BOOLEANS_TRUE and \
        module.tag not in disabled:
        enabled.add(module.tag)
      elif module.tag not in enabled:
        disabled.add(module.tag)
    
    disabled.add('__init__') # hack, kinda; this isn't a module
    
    return enabled, disabled
  
  def _validate_configs(self):
    Event.logger.log(0, L0("validating config"))
    
    Event.logger.log(1, L1("dimsbuild.conf"))
    Event.mcvalidator.validate('/dimsbuild', schema_file='dimsbuild.rng')
    
    Event.logger.log(1, L1(P(Event.config.file).basename))
    # validate individual sections of distro.conf
    Event.validator.validate('/distro/main', schema_file='main.rng')
    for e in self.dispatch:
      e.validate()
    # validate top-level elements
    Event.validator.validateElements(self.disabled_modules)
  
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
    Event.logger = make_log(options.logthresh, options.logfile)
    
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
    Event.CACHE_DIR    = P(mainconfig.get('/dimsbuild/cache/path/text()',
                                          '/var/cache/dimsbuild'))
    Event.TEMP_DIR     = P('/tmp/dimsbuild')
    Event.METADATA_DIR = Event.CACHE_DIR  / base_vars['pva']
    
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
    Event.cache_callback = BuildSyncCallback(Event.logger, Event.METADATA_DIR)
    Event.copy_handler = sync.CopyHandler()
    Event.link_handler = link.LinkHandler()
    
    Event.files_callback = FilesCallback(Event.logger, Event.METADATA_DIR)
    
    Event.mcvalidator = MainConfigValidator(Event.SHARE_DIR/'schemas',
                                            Event.mainconfig.file)
    Event.validator = ConfigValidator(Event.SHARE_DIR/'schemas/distro.conf',
                                      Event.config.file)
  
  def _log_header(self):
    Event.logger.logfile.write(0, "\n\n\n")
    Event.logger.log(0, "Starting build of '%s' at %s" % (Event.fullname, time.strftime('%Y-%m-%d %X')))
    Event.logger.log(4, "Loaded modules: %s" % Event.cvars['loaded-modules'])
    Event.logger.log(4, "Event list: %s" % [ e.id for e in self.dispatch._top ])
  def _log_footer(self):
    Event.logger.log(0, "Build complete at %s" % time.strftime('%Y-%m-%d %X'))


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
