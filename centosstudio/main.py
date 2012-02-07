
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
"""
main.py

Python script defining the Build class, the primary controller for the CentOS Studio.
"""

__author__  = 'Daniel Musgrave <dmusgrave@centossolutions.com>'
__version__ = '3.0'
__date__    = 'June 26th, 2007'

import errno
import imp
import os
import re
import sys
import textwrap
import time

from rpmUtils.arch import getBaseArch

from centosstudio.util import dispatch
from centosstudio.util import listfmt
from centosstudio.util import lock
from centosstudio.util import pps
from centosstudio.util import rxml
from centosstudio.util import shlib
from centosstudio.util import si

from centosstudio.util import sync
from centosstudio.util.sync import cache
from centosstudio.util.sync import link

from centosstudio.callback  import (SyncCallback, CachedSyncCallback,
                                    LinkCallback, SyncCallbackCompressed)
from centosstudio.constants import *
from centosstudio.errors    import (CentOSStudioEventErrorHandler, 
                                    CentOSStudioEventError,
                                    CentOSStudioError)
from centosstudio.event     import Event, CLASS_META
from centosstudio.cslogging import make_log, L0, L1, L2
from centosstudio.validate  import (CentOSStudioValidationHandler,
                                    InvalidEventError)

from centosstudio.event.loader import Loader

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

DEFAULT_CACHE_DIR = pps.path('/var/cache/centosstudio')
DEFAULT_SHARE_DIR = pps.path('/usr/share/centosstudio')
DEFAULT_LOG_FILE = pps.path('/var/log/centosstudio.log')

# map our supported archs to the highest arch in that arch 'class'
ARCH_MAP = {'i386': 'athlon', 'x86_64': 'x86_64'}

# the following chars are allowed in filenames...
FILENAME_REGEX = re.compile('^[a-zA-Z0-9_\-\.]+$')

class Build(CentOSStudioEventErrorHandler, CentOSStudioValidationHandler, object):
  """
  Primary build class - framework upon which a custom centosstudio is generated

  Build consists mostly of variable values  and a dispatch object,  which
  is responsible  for calling  module events  in order to perform various
  build tasks.  It also contains a logger for printing out information to
  the screen.

  The  build  object  is  responsible for  loading  and initializing  all
  program  modules.   It  also  applies  configuration  and  command-line
  arguments to its own internal variables as well as the its dispatcher.

  See dispatch.py  for more information on the role of the  dispatcher in
  the build process.
  """

  def __init__(self, options, arguments, callback=None):
    """
    Initialize a Build object

    Accepts three parameters:
      options:   an  optparse.Options  object  with  the  command  line
                 arguments encountered during command line parsing
      arguments: a list of arguments not processed by the parser
      callback:  a callback object providing set_debug and set_logger functions

    These parameters are normally passed in from the command-line handler
    ('/usr/bin/centosstudio')
    """

    # set up temporary logger - console only
    self.logger = make_log(options.logthresh)
    if callback: callback.set_logger(self.logger)

    # set initial debug value from options
    self.debug = False
    if options.debug is not None:
      self.debug = options.debug
    if callback: callback.set_debug(self.debug)

    # set up configs
    try:
      self._get_config(options, arguments)
      self._get_definition(options, arguments)
    except Exception, e:
      raise CentOSStudioError(e)

    # now that we have mainconfig, use it to set debug mode, if specified
    if self.mainconfig.pathexists('/centosstudio/debug'):
      self.debug = self.mainconfig.getbool('/centosstudio/debug', False)
    if callback: callback.set_debug(self.debug)

    # set up initial variables
    qstr = '/*/main/%s/text()'
    try:
      self.name     = self.definition.get(qstr % 'name')
      self.version  = self.definition.get(qstr % 'version')
      self.arch     = self.definition.get(qstr % 'arch', 'i386')
      self.type        = self.definition.get(qstr % 'type', 'system')
    except rxml.errors.XmlPathError, e:
      raise CentOSStudioError("Validation of %s failed. %s" % 
                            (self.definition.getroot().file, e))

    self.solutionid  = self.definition.get(qstr % 'id',
                          '%s-%s-%s' % (self.name,
                                          self.version,
                                          self.arch))


    # validate initial variables
    self._validate_initial_variables()

    # expand global macros, module macros handled during validation
    map = {'%{name}':     self.name,
           '%{version}':  self.version,
           '%{arch}':     self.arch,
           '%{id}':       self.solutionid,
           }

    try: 
      # top-level macros
      self.definition.resolve_macros(xpaths=['/*', '/*/main/'], map=map)
    except rxml.errors.ConfigError, e:
      raise CentOSStudioError(e)

    # set up real logger - console and file, unless provided as init arg
    self.logfile = ( pps.path(options.logfile)
                     or self.definition.getpath(
                        '/*/main/log-file/text()', None)
                     or self.mainconfig.getpath(
                        '/centosstudio/log-file/text()', None)
                     or DEFAULT_LOG_FILE ).expand().abspath()
    try:
      self.logger = make_log(options.logthresh, self.logfile)
    except IOError, e:
      raise CentOSStudioError("Error opening log file for writing: %s" % e)
    if callback: callback.set_logger(self.logger)

    # set up additional attributes for use by events
    self._compute_event_attrs(options)

    # change working dir to config dir so relative paths expand properly
    os.chdir(self.definition.file.dirname)

    # set up import_dirs
    import_dirs = self._compute_import_dirs(options)

    # set up lists of enabled and disabled modules
    enabled, disabled = self._compute_modules(options)

    # load all enabled modules, register events, set up dispatcher
    loader = Loader(top = AllEvent(ptr = self), api_ver = API_VERSION,
                    enabled = enabled, disabled = disabled,
                    load_extensions = False)

    try:
      self.dispatch = dispatch.Dispatch(
                        loader.load(import_dirs, prefix='centosstudio/modules',
                                    ptr = self)
                      )
      self.disabled_modules = loader.disabled
      self.enabled_modules  = loader.enabled
      self.module_map       = loader.module_map

      # add module mappings for pseudo events
      for modid, module in loader.modules.items():
        self.module_map.setdefault('all', []).extend(self.module_map[modid])
        grp = module.MODULE_INFO.get('group')
        if grp:
          self.module_map.setdefault(grp, []).extend(self.module_map[modid])

    except ImportError, e:
      raise CentOSStudioError("Error loading core centosstudio files: %s" % e)

    except InvalidEventError, e:
      raise CentOSStudioError("\n%s" % e)

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

    # perform validation, if not specified otherwise
    if not options.no_validate:
      self.validate_configs()
      if options.validate_only:
        print self.definition
        sys.exit()

    # set up locking
    self._lock = lock.Lock( 'centosstudio-%s.pid' % self.solutionid )

  def main(self):
    "Build a solution repository"
    if self._lock.acquire():
      self._log_header()
      try:
        try:
          self.dispatch.execute(until=None)
        except CentOSStudioEventError, e:
          self._handle_Exception(e)
      finally:
        self._lock.release()
      self._log_footer()
    else:
      raise CentosStudioError("Another instance of centosstudio (pid %d) is "
                              "already modifying '%s'" % 
                              (self._lock._readlock()[0], self.solutionid ))

  def _get_config(self, options, arguments):
    """
    Gets the centosstudio config based on option values. The centosstudio
    config file is optional; if not found, merely uses a set of default values.
    """
    cp = pps.path(options.mainconfigpath).expand().abspath()
    if cp and cp.exists():
      self.logger.log(4, "Reading '%s'" % cp)
      mc = rxml.config.parse(cp).getroot()
    else:
      self.logger.log(4, "No centosstudio config file found at '%s'. Using default settings" % cp)
      mc = rxml.config.fromstring('<centosstudio/>')

    self.mainconfig = mc

  def _get_definition(self, options, arguments):
    """
    Gets the definition based on option values. A definition file is
    required, except in the event that the '-h' or '--help' argument was given
    on the command line, in which case the definition file can be omitted or
    not exist.  (This previous allowance is so that a user can type
    `centosstudio -h` on the command line without giving the '-c' option.) 
    """
    dp = pps.path(arguments[0]).expand().abspath()
    if not dp.exists():
      raise rxml.errors.ConfigError("No definition found at '%s'" % dp)
    self.logger.log(3, "Reading '%s'" % dp)
    dt = rxml.config.parse(dp)
    self.definitiontree = dt
    self.definition = dt.getroot()

  def _validate_initial_variables(self):
    for elem in ['name', 'version', 'solutionid']:
      if not FILENAME_REGEX.match(eval('self.%s' % elem)):
        raise CentOSStudioError("Validation of %s failed. "
          "The 'main/%s' element contains an invalid value '%s'. "
          "Accepted characters are a-z, A-Z, 0-9, _, ., and -."
          % (self.definition.getroot().file, elem, eval('self.%s' % elem)))
      
    if not self.arch in ARCH_MAP:
      raise CentOSStudioError("Validation of %s failed. "
        "The 'main/arch' element contains an invalid value '%s'. "
        "Accepted values are 'i386' and 'x86_64'."
        % (self.definition.getroot().file, self.arch))

    if not self.version in ['5', '6']:
      raise CentOSStudioError("Validation of %s failed. "
        "The 'main/version' element contains an invalid value '%s'. "
        "Accepted values are '5' and '6'."
        % (self.definition.getroot().file, self.version))

    # if type is component, ensure system is configured host virtual machines
    if self.type == 'component':
      try:
        import libvirt
      except ImportError:
        raise CentOSStudioError(
          "Error: The 'main/type' element of the definition file at '%s' is "
          "set to 'component', but this machine is not configured to build "
          "components. See the CentOS Studio User Manual for information "
          "on system requirements for building components, which include "
          "hardware and software support for hosting virtual machines."
          % (self.definition.getroot().file))

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
        raise CentOSStudioError("Module '%s' does not exist or was not loaded"
                                % moduleid)
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
      raise CentOSStudioError("Unregistered event '%s'" % eventid)
    if not e._check_status(status):
      raise CentOSStudioError("Cannot %s protected event '%s'" % (str, eventid))
    e.status = status

  def _compute_import_dirs(self, options):
    """
    Compute a list of directories to try importing from

    options    : an optparse.Values instance containing the result of parsing
                 command line options
    """
    import_dirs = [ x.expand().abspath() for x in \
      self.mainconfig.getpaths('/centosstudio/lib-path/text()', []) ]

    if options.libpath:
      import_dirs = [ pps.path(x).expand().abspath() for x in options.libpath ] + import_dirs
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(pps.path(dir))

    return import_dirs

  def _compute_modules(self, options):
    """
    Compute a list of modules centosstudio should not load.  Disabling takes priorty
    over enabling.

    options      : an optparse.Values instance containing the result of
                   parsing command line options
    """
    enabled  = set(options.enabled_modules)
    disabled = set(options.disabled_modules)

    # enable/disable modules from app config
    for module in self.definition.xpath('/*/*'):
      if module.tag == 'main': continue # main isn't a module
      if not module.getbool('@enabled', 'True'):
        disabled.add(module.tag)
      else:
        enabled.add(module.tag)

    # enable/disable modules from main config
    for module in self.mainconfig.xpath('/centosstudio/enable-module', []):
      enabled.add(module.text)
    for module in self.mainconfig.xpath('/centosstudio/disable-module', []):
      disabled.add(module.text)

    disabled.add('__init__') # hack, kinda; these are loaded automatically

    return enabled, disabled

  def _compute_event_attrs(self, options):
    """
    Set up a bunch of additional variables for use by events. The Event
    object sets these up as convenience variables by calling get_event_attrs
    in its __init__ method.

    options: an OptionParser.Options  object  with  the  command  line
             arguments encountered during command line parsing
    """
    # Event.cvars is a list of program 'control variables' - modules can use
    # this to communicate between themselves as necessary
    self.cvars = CvarsDict()

    # set up misc vars from the main config element
    qstr = '/*/main/%s/text()'
    self.basearch    = getBaseArch(ARCH_MAP[self.arch])
    self.fullname    = self.definition.get(qstr % 'fullname', self.name)
    self.packagepath = 'Packages'
    self.webloc      = self.definition.get(qstr % 'bug-url', 
                                                  'No bug url provided')

    # set up other directories
    self.CACHE_DIR    = self.mainconfig.getpath(
                        '/centosstudio/cache/path/text()',
                        DEFAULT_CACHE_DIR).expand().abspath()
    self.METADATA_DIR = self.CACHE_DIR  / self.solutionid

    sharedirs = [ DEFAULT_SHARE_DIR ]
    sharedirs.extend(reversed([ x.expand().abspath()
      for x in self.mainconfig.getpaths(
        '/centosstudio/share-path/text()', []) ]))
    sharedirs.extend(reversed([ pps.path(x).expand().abspath()
      for x in options.sharepath ]))

    # reverse the order so we get cli options, then config, then defaults
    self.sharedirs = [ x for x in reversed(sharedirs) ]
    assert self.sharedirs
    for d in self.sharedirs:
      if not d==DEFAULT_SHARE_DIR and not d.isdir():
        raise RuntimeError("The specified share-path '%s' does not exist." %d)

    cache_max_size = self.mainconfig.get('/centosstudio/cache/max-size/text()', '30GB')
    if cache_max_size.isdigit():
      cache_max_size = '%sGB' % cache_max_size
    self.CACHE_MAX_SIZE = si.parse(cache_max_size)

    self.cache_handler = cache.CachedSyncHandler(
                         cache_dir = self.CACHE_DIR / '.cache',
                         cache_max_size = self.CACHE_MAX_SIZE)
    self.copy_handler = sync.CopyHandler()
    self.link_handler = link.LinkHandler(allow_xdev=True)

    self.copy_callback  = SyncCallback(self.logger, self.METADATA_DIR)
    self.cache_callback = CachedSyncCallback(self.logger, self.METADATA_DIR)
    self.link_callback  = LinkCallback(self.logger, self.METADATA_DIR)
    self.copy_callback_compressed = SyncCallbackCompressed(
                                     self.logger, self.METADATA_DIR)

    selinux_enabled = False
    try:
      selinux_enabled = shlib.execute('/usr/sbin/getenforce')[0] != 'Disabled'
    except:
      pass
    self.cvars['selinux-enabled'] = selinux_enabled

    # Expose options object for events (e.g. build-machine) that run parallel
    # instances of the Build object
    self.options = options

  def _log_header(self):
    self.logger.logfile.write(0, "\n\n\n")
    self.logger.log(1, "Starting build of '%s' at %s" % (self.solutionid, time.strftime('%Y-%m-%d %X')))
    self.logger.log(4, "Loaded modules: %s" % self.cvars['loaded-modules'])
    self.logger.log(4, "Event list: %s" % [ e.id for e in self.dispatch._top ])
  def _log_footer(self):
    self.logger.log(1, "Build complete at %s" % time.strftime('%Y-%m-%d %X'))


  ###### Helper Methods ######
  def get_event_attrs(self, ptr):
    """
    Called by Event.__init__() to set up a bunch of convenience variables for
    event instances.
    """
    ptr.cvars = self.cvars 
    ptr.logger = self.logger
    ptr.mainconfig  = self.mainconfig
    ptr._config     = self.definition
    ptr._configtree = self.definitiontree
  
    # set up base variables
    di = ptr.cvars['distribution-info'] = {}
    qstr = '/*/main/%s/text()'
  
    di['name']              = self.name 
    di['version']           = self.version
    di['arch']              = self.arch
    di['type']              = self.type
    di['basearch']          = self.basearch
    di['solutionid']        = self.solutionid
    di['anaconda-version']  = None
    di['fullname']          = self.fullname
    di['packagepath']       = 'Packages'
    di['webloc']            = self.webloc
  
    for k,v in di.items():
      setattr(ptr, k, v)
  
    # set up other directories
    ptr.CACHE_DIR    = self.CACHE_DIR
    ptr.METADATA_DIR = self.METADATA_DIR 
    ptr.SHARE_DIRS   = self.sharedirs
    ptr.CACHE_MAX_SIZE = self.CACHE_MAX_SIZE
  
    ptr.cache_handler = self.cache_handler
    ptr.copy_handler = self.copy_handler
    ptr.link_handler = self.link_handler

    ptr.copy_callback  = self.copy_callback
    ptr.cache_callback = self.cache_callback
    ptr.link_callback  = self.link_callback
    ptr.copy_callback_compressed = self.copy_callback_compressed


###### Classes ######
class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)


class AllEvent(Event):
  "Top level event that is the ancestor of all other events.  Changing this "
  "event's version will cause all events to automatically run."
  moduleid = None
  def __init__(self, ptr):
    Event.__init__(self,
      id = 'all',
      ptr = ptr,
      version = 1.01,
      properties = CLASS_META,
      suppress_run_message = True
    )
