"""
main.py

Python script defining the Build class, the primary controller for the Spin.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '3.0'
__date__    = 'June 26th, 2007'

DEBUG = True # enable to print tracebacks; disable for 'release mode'

import imp
import os
import sys
import time

from rpmUtils.arch import getBaseArch
from StringIO      import StringIO

from rendition import dispatch
from rendition import pps
from rendition import si
from rendition import xmllib

from rendition import sync
from rendition.sync import cache
from rendition.sync import link

from spin.callback  import (SyncCallback, CachedSyncCallback, LinkCallback,
                            SyncCallbackCompressed)
from spin.constants import *
from spin.event     import Event, CLASS_META
from spin.logging   import make_log, L0, L1, L2
from spin.validate  import (ConfigValidator, MainConfigValidator,
                            InvalidConfigError, InvalidSchemaError)

from spin.event.loader import Loader

P = pps.Path # convenience, same is used throughout most modules

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0
LOCK = P('/var/run/spin.pid')

DEFAULT_TEMP_DIR = P('/tmp/spin')
DEFAULT_CACHE_DIR = P('/var/cache/spin')
DEFAULT_SHARE_DIR = P('/usr/share/spin')

# map our supported archs to the highest arch in that arch 'class'
ARCH_MAP = {'i386': 'athlon', 'x86_64': 'x86_64'}

class Build(object):
  """
  Primary build class - framework upon which a custom spin is generated

  Build consists mostly of variable values  and a dispatch object,  which
  is responsible  for calling  module events  in order to perform various
  build tasks.  It also contains a logger for printing out information to
  the screen.

  The  build  object  is  responsible for  loading  and initializing  all
  program  modules  and  plugins.   It  also  applies  configuration  and
  command-line arguments to its own internal variables as well as the its
  dispatcher.

  See dispatch.py  for more information on the role of the  dispatcher in
  the build process.
  """

  def __init__(self, options, arguments, parser):
    """
    Initialize a Build object

    Accepts two parameters:
      options:   an  optparse.Options  object  with  the  command  line
                 arguments encountered during command line parsing
      arguments: a list of arguments not processed by the parser
      parser:    the optparse.OptionParser instance used to parse these
                 command line arguments

    These parameters are normally passed in from the command-line handler
    ('/usr/bin/spin')
    """
    self.parser = parser

    # set up loger
    self.logger = make_log(options.logthresh, options.logfile)

    # set up configs
    self._get_config(options, arguments)

    # set up import_dirs
    import_dirs = self._compute_import_dirs(options)

    # set up lists of enabled and disabled modules
    enabled, disabled = self._compute_modules(options)

    # set up event superclass so that it contains good default values
    self._seed_event_defaults(options)

    # load all enabled modules, register events, set up dispatcher
    loader = Loader(top = AllEvent(), api_ver = API_VERSION,
                    enabled = enabled, disabled = disabled)

    try:
      self.dispatch = dispatch.Dispatch(
                        loader.load(import_dirs, prefix='spin/modules')
                      )
      self.disabled_modules = loader.disabled
      self.enabled_modules  = loader.enabled
      self.module_map       = loader.module_map
      # hack to make sure '--force all' still works #!
      # or is it a hack?  Perhaps we should consider adding 
      # arbitrary containers of higher level tasks - all installer files,
      # all software and custom rpms, all publish stuff, etc
      self.module_map.setdefault('all', []).append(self.dispatch._top.id)
    except ImportError, e:
      Event.logger.log(0, L0("Error loading core spin files: %s" % e))
      if DEBUG: raise
      sys.exit(1)

    # list events, if requested
    if options.list_events:
      self.dispatch.pprint()
      sys.exit()

    # apply --force to modules/events
    for eventid in self._compute_events(options.force_modules,
                                        options.force_events):
      self._set_status(eventid, True, '--force')

    # apply --skip to modules/events
    for eventid in self._compute_events(options.skip_modules,
                                        options.skip_events):
      self._set_status(eventid, False, '--skip')

    # clear cache, if requested
    if options.clear_cache:
      Event.logger.log(1, L0("clearing cache"))
      Event.cache_handler.cache_dir.listdir(all=True).rm(recursive=True)

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


  def main(self):
    "Build a distribution"
    self._log_header()
    self._lock()
    try:
      self.dispatch.execute(until=None)
    finally:
      self._unlock()
    DEFAULT_TEMP_DIR.rm(recursive=True, force=True) # clean up temp dir
    self._log_footer()

  def _get_config(self, options, arguments):
    """
    Gets the main config and distro configs based on option values.  Main
    config file is optional; if not found, merely uses a set of default
    values.  Distro config is required, except in the event that the '-h' or
    '--help' argument was given on the command line, in which case the distro
    config file can be omitted or not exist.  (This previous allowance is so
    that a user can type `spin -h` on the command line without giving
    the '-c' option.)
    """
    mcp = P(options.mainconfigpath)
    dcp = P(arguments[0])
    try:
      if mcp and mcp.exists():
        self.logger.log(4, "Reading main config file '%s'" % mcp)
        mc = xmllib.config.read(mcp)
      else:
        self.logger.log(4, "No main config file found at '%s'. Using default settings" % mcp)
        mc = xmllib.config.read(StringIO('<spin/>'))

      dcp = dcp.expand().abspath()
      if not dcp.exists():
        raise xmllib.config.ConfigError("No config file found at '%s'" % dcp)

      self.logger.log(3, "Reading distro config file '%s'" % dcp)
      dc = xmllib.config.read(dcp)
    except xmllib.tree.XmlSyntaxError, e:
      self.logger.log(0, "Error reading config file: %s" % e)
      raise

    self.mainconfig = mc
    self.distroconfig = dc

  def _compute_events(self, modules=None, events=None):
    """
    Compute the set of events contained in the list of modules and events
    given as arguments.  (Used to --force or --skip all events requested by
    the command line arguments of the same name.)

    modules : a list of module ids
    events  : a list of event ids
    """
    r = set() # set of eventids to force
    for moduleid in modules or []:
      try:
        r.update(self.module_map[moduleid])
      except KeyError:
        Event.logger.log(0, L0("Module '%s' does not exist or was not loaded" % moduleid))
        sys.exit(1)
    r.update(events or [])
    return r

  def _set_status(self, eventid, status, str):
    """
    Helper method to set the status of an event (--force/--skip)

    eventid : the id of the event
    status  : the value to set Event.status to (True for --force, False for
              --skip, None for default)
    str     : a string identifying the action being performed; used only
              for logging purposes (typically '--force' when status is True,
              '--skip' when status is False)
    """
    try:
      e = self.dispatch.get(eventid)
    except dispatch.UnregisteredEventError:
      Event.logger.log(0, L0("Unregistered event '%s'" % eventid))
      sys.exit(1)
    if not e._check_status(status):
      Event.logger.log(0, L0("Cannot %s protected event '%s'" % (str, eventid)))
      sys.exit(1)
    e.status = status

  def _compute_import_dirs(self, options):
    """
    Compute a list of directories to try importing from

    options    : an optparse.Values instance containing the result of parsing
                 command line options
    """
    import_dirs = [ P(x).expand() for x in \
      self.mainconfig.xpath('/spin/library-path/text()', []) ]

    if options.libpath:
      import_dirs = [ P(x).expand() for x in options.libpath ] + import_dirs
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(P(dir))

    return import_dirs

  def _compute_modules(self, options):
    """
    Compute a list of modules spin should not load.  Disabling takes priorty
    over enabling.

    options      : an optparse.Values instance containing the result of
                   parsing command line options
    """
    enabled  = set(options.enabled_modules)
    disabled = set(options.disabled_modules)

    # enable/disable modules from distro config
    for module in self.distroconfig.xpath('/distro/*'):
      if module.tag == 'main': continue # main isn't a module
      if module.get('@enabled', 'True') in BOOLEANS_FALSE:
        disabled.add(module.tag)
      else:
        enabled.add(module.tag)

    # enable/disable modules from main config
    for module in self.mainconfig.xpath('/spin/modules/module', []):
      if module.get('@enabled', 'True') in BOOLEANS_FALSE:
        disabled.add(module.text)
      # don't add modules to enabled list if they're not disabled

    disabled.add('__init__') # hack, kinda; these are loaded automatically

    return enabled, disabled

  def _validate_configs(self):
    "Validate main config and distro config"
    Event.logger.log(0, L0("validating config"))

    Event.logger.log(1, L1("spin.conf"))
    mcvalidator = MainConfigValidator([ x/'schemas' for x in Event.SHARE_DIRS ],
                                      self.mainconfig.file)
    mcvalidator.validate('/spin', schema_file='spin.rng')

    # validate individual sections of distro.conf
    Event.logger.log(1, L1(P(Event._config.file).basename))
    validator = ConfigValidator([ x/'schemas/distro.conf' for x in Event.SHARE_DIRS ],
                                self.distroconfig.file)

    # validate the main section
    validator.validate('main', schema_file='main.rng')

    # validate all event top-level sections
    validated = [] # list of already-validated modules (so we don't revalidate)
    for e in self.dispatch:
      element_name = e.__module__.split('.')[-1]
      if element_name in validated: continue # don't re-validate
      validator.validate(element_name, schema_file='%s.rng' % element_name)
      validated.append(element_name)

    # verify top-level elements
    validator.config = Event._config
    validator.verify_elements(self.disabled_modules)

    # allow events to validate other things not covered in schema
    for e in self.dispatch:
      e.validate()

  def _seed_event_defaults(self, options):
    """
    Set up a bunch of variables in the Event superclass that all subclasses
    inherit automatically.

    options: an  OptionParser.Options  object  with  the  command  line
             arguments encountered during command line parsing
    """
    # Event.cvars is a list of program 'control variables' - modules can use
    # this to communicate between themselves as necessary
    Event.cvars = CvarsDict()

    # set up loggers
    Event.logger = self.logger

    # set up config dirs
    Event.mainconfig = self.mainconfig
    Event._config    = self.distroconfig

    # set up base variables
    bv = Event.cvars['base-vars'] = {}
    qstr = '/distro/main/%s/text()'

    bv['arch']     = ARCH_MAP[Event._config.get(qstr % 'arch', 'i386')]
    bv['product']  = Event._config.get(qstr % 'product')
    bv['version']  = Event._config.get(qstr % 'version')
    bv['basearch'] = getBaseArch(bv['arch'])
    bv['fullname'] = Event._config.get(qstr % 'fullname', bv['product'])
    bv['webloc']   = Event._config.get(qstr % 'bug-url', 'No bug url provided')
    bv['pva']      = '%(product)s-%(version)s-%(basearch)s' % bv
    bv['productpath'] = Event._config.get(qstr % 'product-path', 'Packages')
    bv['copyright'] = Event._config.get(qstr % 'copyright', '')

    for k,v in bv.items():
      setattr(Event, k, v)

    # set up other directories
    Event.CACHE_DIR    = P(self.mainconfig.get('/spin/cache/path/text()',
                                               DEFAULT_CACHE_DIR))
    Event.TEMP_DIR     = DEFAULT_TEMP_DIR
    Event.METADATA_DIR = Event.CACHE_DIR  / bv['pva']

    Event.SHARE_DIRS = [ P(x).expand() for x in \
                         self.mainconfig.xpath('/spin/share-path/text()',
                                               [DEFAULT_SHARE_DIR]) ]

    if options.sharepath:
      options.sharepath.extend(Event.SHARE_DIRS)
      Event.SHARE_DIRS = [ P(x).expand() for x in options.sharepath ]

    Event.CACHE_MAX_SIZE = \
      si.parse(self.mainconfig.get('/spin/cache/max-size/text()', '30GiB'))

    Event.cache_handler = cache.CachedSyncHandler(
                            cache_dir = Event.CACHE_DIR / '.cache',
                            cache_max_size = Event.CACHE_MAX_SIZE,
                          )
    Event.copy_handler = sync.CopyHandler()
    Event.link_handler = link.LinkHandler(allow_xdev=True)

    Event.copy_callback  = SyncCallback(Event.logger, Event.METADATA_DIR)
    Event.cache_callback = CachedSyncCallback(Event.logger, Event.METADATA_DIR)
    Event.link_callback  = LinkCallback(Event.logger, Event.METADATA_DIR)
    Event.copy_callback_compressed = SyncCallbackCompressed(
                                     Event.logger, Event.METADATA_DIR)

  def _log_header(self):
    Event.logger.logfile.write(0, "\n\n\n")
    Event.logger.log(0, "Starting build of '%s %s %s' at %s" % (Event.fullname, Event.version, Event.basearch, time.strftime('%Y-%m-%d %X')))
    Event.logger.log(4, "Loaded modules: %s" % Event.cvars['loaded-modules'])
    Event.logger.log(4, "Event list: %s" % [ e.id for e in self.dispatch._top ])
  def _log_footer(self):
    Event.logger.log(0, "Build complete at %s" % time.strftime('%Y-%m-%d %X'))

  # def locking methods
  def _lock(self):
    if LOCK.exists():
      try:
        pid = int(LOCK.read_lines()[0])
        if pid != os.getpid():
          raise RuntimeError("there is already an instance of spin running (pid %d)" % pid)
      except:
        LOCK.remove()
    LOCK.touch()
    LOCK.write_lines([str(os.getpid())])
  def _unlock(self):
    if LOCK.exists(): LOCK.remove()

class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)


class AllEvent(Event):
  "Top level event that is the ancestor of all other events.  Changing this "
  "event's version will cause all events to automatically run."
  def __init__(self):
    Event.__init__(self,
      id = 'all',
      version = 0,
      properties = CLASS_META,
      suppress_run_message = True
    )
