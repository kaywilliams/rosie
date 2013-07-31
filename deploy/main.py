
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

Python script defining the Build class, the primary controller for the Deploy.
"""

__author__  = 'Daniel Musgrave <dmusgrave@deployproject.org>'
__version__ = '3.0'
__date__    = 'June 26th, 2007'

import errno
import imp
import lxml 
import os
import re
import sys
import textwrap
import traceback
import time

from deploy.util import dispatch
from deploy.util import listfmt
from deploy.util import lock
from deploy.util import rxml
from deploy.util import shlib
from deploy.util import si

from deploy.util import pps
from deploy.util.pps.Path.error import OfflinePathError

from deploy.util import sync

from deploy.callback  import (SyncCallback, CachedCopyCallback,
                              LinkCallback, SyncCallbackCompressed)
from deploy.constants import *
from deploy.errors    import (DeployEventErrorHandler, 
                                    DeployEventError,
                                    DeployError,
                                    InvalidOptionError,
                                    InvalidConfigError)
from deploy.event     import Event, CLASS_META
from deploy.dlogging import make_log, L0, L1, L2
from deploy.validate  import (DeployValidationHandler,
                                    InvalidEventError)

from deploy.event.loader import Loader

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

DEFAULT_CACHE_DIR = pps.path('/var/cache/deploy')
DEFAULT_LIB_DIR = pps.path('/var/lib/deploy')
DEFAULT_SHARE_DIR = pps.path('/usr/share/deploy')
DEFAULT_TEMPLATES_DIR = pps.path('/usr/share/deploy/templates')
DEFAULT_LOG_FILE = pps.path('/var/log/deploy.log')

# supported base distribution versions
OS_LIST = ['centos', 'rhel']
OS_ERROR = "Accepted values are '%s'." % "', '".join(OS_LIST)

# map our supported archs to the highest arch in that arch 'class'
ARCH_MAP = {'i386': 'athlon', 'x86_64': 'x86_64'}
ARCH_ERROR = "Accepted values are '%s'." % "', '".join(ARCH_MAP)

# supported base distribution versions
VERSIONS = ['5', '6']
VERSIONS_ERROR = ("Accepted values are '%s'." % 
                  "', '".join(VERSIONS))

# the following chars are allowed in filenames...
FILENAME_REGEX = '^[a-zA-Z0-9_\-]+$'
FILENAME_ERROR = "Accepted characters are a-z, A-Z, 0-9, _, and -."

VALIDATE_DATA = {
    'name':    { 'validatefn': lambda x: re.match(FILENAME_REGEX, x),
                 'error':      FILENAME_ERROR},
    'os':      { 'validatefn': lambda x: x in OS_LIST,
                 'error':      OS_ERROR},
    'version': { 'validatefn': lambda x: x in VERSIONS,
                 'error':      VERSIONS_ERROR},
    'arch':    { 'validatefn': lambda x: x in ARCH_MAP,
                 'error':      ARCH_ERROR},
    'id':      { 'validatefn': lambda x: re.match(FILENAME_REGEX, x),
                 'error':      FILENAME_ERROR},}


class Build(DeployEventErrorHandler, DeployValidationHandler, object):
  """
  Primary build class - framework upon which a custom deploy is generated

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
    ('/usr/bin/deploy')
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
      self._get_definition_path(arguments)
      self._get_templates_dir()
      self._get_initial_macros(options)
      self._get_definition(options, arguments)
    except rxml.errors.XmlError, e:
      if self.debug: 
        raise
      else:
        raise DeployError(e)

    # now that we have mainconfig, use it to set debug mode, if specified
    if self.mainconfig.pathexists('/deploy/debug'):
      self.debug = self.mainconfig.getbool('/deploy/debug', False)
    if callback: callback.set_debug(self.debug)

    # set up initial variables
    qstr = '/*/main/%s/text()'

    for elem in ['name', 'os', 'version', 'arch', 'id']:
      try:
        exec ("self.%s = self.definition.getxpath('/*/main/%s/text()')" 
              % (elem, elem))
      except rxml.errors.XmlPathError, e:
        msg = ("ERROR: Validation of %s failed. Missing required 'main/%s' "
               "element." % (self.definition.getroot().getbase(), elem))
        raise DeployError(msg)

    self.type   = self.definition.getxpath(qstr % 'type', 'system')
    self.build_id = self.definition.getxpath(qstr % 'id', '%s-%s-%s-%s' % 
                               (self.name, self.os, self.version, self.arch))

    # validate initial variables
    for elem in VALIDATE_DATA:
      if elem == 'id':
        value = self.build_id
      else: 
        value = eval('self.%s' % elem)
      if not VALIDATE_DATA[elem]['validatefn'](value):
        raise InvalidConfigError(self.definition.getbase(), elem, value, 
                                 VALIDATE_DATA[elem]['error'])
    
    # set data_dir
    # wish we could do this before get_definition() for parity with other 
    # global-runtime macros, but we don't have the build-id until after the
    # definition has been read.
    self._get_data_dir(options)

    # set up real logger - console and file, unless provided as init arg
    self.logfile = ( pps.path(options.logfile)
                     or self.definition.getpath(
                        '/*/main/log-file/text()', None)
                     or self.mainconfig.getpath(
                        '/deploy/log-file/text()', None)
                     or DEFAULT_LOG_FILE ).expand().abspath()
    try:
      self.logger = make_log(options.logthresh, self.logfile)
    except IOError, e:
      raise DeployError("Error opening log file for writing: %s" % e)
    if callback: callback.set_logger(self.logger)

    # set up additional attributes for use by events
    self._compute_event_attrs(options)

    # change working dir to config dir so relative paths expand properly
    os.chdir(self.definition.getbase().dirname)

    # set up import_dirs
    import_dirs = self._compute_import_dirs(options)

    # set up lists of enabled and disabled modules
    enabled, disabled = self._compute_modules(options)

    # load all enabled modules, register events, set up dispatcher
    loader = Loader(ptr=self, top=AllEvent(ptr = self), api_ver=API_VERSION,
                    enabled=enabled, disabled=disabled,
                    load_extensions=False)

    try:
      self.dispatch = dispatch.Dispatch(
                      loader.load(import_dirs, prefix='deploy/modules',))
      self.disabled_modules = loader.disabled
      self.enabled_modules  = loader.enabled
      self.module_map       = loader.module_map

      # add module mappings for pseudo events
      for modid, module in loader.modules.items():
        self.module_map.setdefault('all', []).extend(self.module_map[modid])
        grp = loader.module_info[modid].get('group', '')
        if grp:
          self.module_map.setdefault(grp, []).extend(self.module_map[modid])

    except ImportError, e:
      raise DeployError("Error loading core deploy files: %s" % 
            traceback.format_exc())

    except InvalidEventError, e:
      raise DeployError("\n%s" % e)

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
    self._lock = lock.Lock( 'deploy-%s.pid' % self.build_id )

  def main(self):
    "Build a repository"
    if self._lock.acquire():
      self._log_header()
      try:
        try:
          self.dispatch.execute(until=None)
        except (DeployEventError, OfflinePathError), e:
          self._handle_Exception(e)
      finally:
        self._lock.release()
      self._log_footer()
    else:
      raise DeployError("\nAnother instance of deploy (pid %d) is "
                              "already modifying '%s'" % 
                              (self._lock._readlock()[0], self.build_id ))


  def _get_config(self, options, arguments):
    """
    Gets the deploy config based on option values. The deploy
    config file is optional; if not found, merely uses a set of default values.
    """
    cp = pps.path(options.mainconfigpath).expand().abspath()
    if cp and cp.exists():
      self.logger.log(4, "Reading '%s'" % cp)
      mc = rxml.config.parse(cp).getroot()
    else:
      self.logger.log(4, "No deploy config file found at '%s'. Using default settings" % cp)
      mc = rxml.config.fromstring('<deploy/>')

    self.mainconfig = mc

  def _get_definition_path(self, arguments):
    self.definition_path = pps.path(arguments[0]).expand().abspath()
    if not self.definition_path.exists():
      raise rxml.errors.XmlError("No definition found at '%s'" % dp)

  def _get_templates_dir(self):
    self.templates_dir = self.mainconfig.getpath(
                         '/deploy/templates-path/text()',
                          DEFAULT_TEMPLATES_DIR)

  def _get_initial_macros(self, options):
    # setup global macros using values from options, if provided 
    map = {}

    if options.macros:
      for pair in options.macros:
        id = pair.split(':')[0].strip()
        value = ':'.join(pair.split(':')[1:]).strip()

        if not id or not value:
          raise InvalidOptionError(pair, 'macro', "Macro options must take the "
                                   "form 'id:value'.")

        # convert string to macro element
        value = rxml.config.fromstring("<macro id='%s'>%s</macro>" %
                                      (id, value)) 

        map['%%{%s}' % id] = value

    map.setdefault('%{definition-dir}', pps.path(self.definition_path).dirname)
    map.setdefault('%{templates-dir}', self.templates_dir)

    self.initial_macros = map

  def _get_definition(self, options, arguments):
    """
    Gets the definition based on option values. A definition file is
    required, except in the event that the '-h' or '--help' argument was given
    on the command line, in which case the definition file can be omitted or
    not exist. (This previous allowance is so that a user can type
    `deploy -h` on the command line without giving the '-c' option.) 
    """
    self.logger.log(3, "Reading '%s'" % self.definition_path)
    dt = rxml.config.parse(self.definition_path, xinclude=True,
                           macros=self.initial_macros,
                           remove_macros=True)
    self.definition = dt.getroot()

  def _get_data_dir(self, options):
    # setup data-dir and data file name
    self.data_root = (pps.path(options.data_root) or 
                      pps.path(self.definition_path).dirname)
    self.data_root.exists() or self.data_root.mkdir()

    self.data_dir = self.data_root / self.build_id
    self.data_dir.exists() or self.data_dir.mkdir()

    self.datfn = self.data_dir / '%s.dat' % self.build_id

    legacy_datfile = self.data_root / '%s.dat' % self.build_id
    if legacy_datfile.exists() and not self.datfn.exists():
      legacy_datfile.move(self.data_dir)

    self.definition.resolve_macros(map={'%{data-dir}': self.data_dir})

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
        raise DeployError("Module '%s' does not exist or was not loaded"
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
      raise DeployError("Unregistered event '%s'" % eventid)
    if not e._check_status(status):
      raise DeployError("Cannot %s protected event '%s'" % (str, eventid))
    e.status = status

  def _compute_import_dirs(self, options):
    """
    Compute a list of directories to try importing from

    options    : an optparse.Values instance containing the result of parsing
                 command line options
    """
    import_dirs = [ x.expand().abspath() for x in \
      self.mainconfig.getpaths('/deploy/lib-path/text()', []) ]

    if options.libpath:
      import_dirs = [ pps.path(x).expand().abspath() for x in options.libpath ] + import_dirs
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(pps.path(dir))

    return import_dirs

  def _compute_modules(self, options):
    """
    Compute a list of modules deploy should not load.  Disabling takes priorty
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
    for module in self.mainconfig.xpath('/deploy/enable-module', []):
      enabled.add(module.text)
    for module in self.mainconfig.xpath('/deploy/disable-module', []):
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
    self.fullname    = self.definition.getxpath(qstr % 'fullname', self.name)
    self.packagepath = 'Packages'
    self.webloc      = self.definition.getxpath(qstr % 'bug-url', 
                                                  'No bug url provided')

    # set up other directories
    self.LIB_DIR      = self.mainconfig.getpath(
                        '/deploy/libdir/path/text()',
                        DEFAULT_LIB_DIR).expand().abspath()
    self.CACHE_DIR    = self.mainconfig.getpath(
                        '/deploy/cache/path/text()',
                        DEFAULT_CACHE_DIR).expand().abspath()
    self.METADATA_DIR = self.CACHE_DIR  / (self.type + 's') / self.build_id

    sharedirs = [ DEFAULT_SHARE_DIR ]
    sharedirs.extend(reversed([ x.expand().abspath()
      for x in self.mainconfig.getpaths(
        '/deploy/share-path/text()', []) ]))
    sharedirs.extend(reversed([ pps.path(x).expand().abspath()
      for x in options.sharepath ]))

    # reverse the order so we get cli options, then config, then defaults
    self.sharedirs = [ x for x in reversed(sharedirs) ]
    assert self.sharedirs
    for d in self.sharedirs:
      if not d==DEFAULT_SHARE_DIR and not d.isdir():
        raise RuntimeError("The specified share-path '%s' does not exist." %d)

    # set up cache options
    cache_max_size = self.mainconfig.getxpath('/deploy/cache/max-size/text()', '30GB')
    if cache_max_size.isdigit():
      cache_max_size = '%sGB' % cache_max_size
    self.CACHE_MAX_SIZE = si.parse(cache_max_size)


    self.cache_handler = pps.cache.CacheHandler(
                         cache_dir = self.CACHE_DIR / '.cache',
                         cache_max_size = self.CACHE_MAX_SIZE,
                         offline = self.mainconfig.getxpath(
                                   '/deploy/offline/text()', 
                                    options.offline))
    self.copy_callback  = SyncCallback(self.logger, self.METADATA_DIR)
    self.cache_callback = CachedCopyCallback(self.logger, self.METADATA_DIR)
    self.link_callback  = LinkCallback(self.logger, self.METADATA_DIR)
    self.copy_callback_compressed = SyncCallbackCompressed(
                                     self.logger, self.METADATA_DIR)

    selinux_enabled = False
    try:
      selinux_enabled = shlib.execute('/usr/sbin/getenforce')[0] != 'Disabled'
    except:
      pass
    self.cvars['selinux-enabled'] = selinux_enabled

    # Expose options object for events (e.g. srpmbuild) that run parallel
    # instances of the Build object
    self.options = options

  def _log_header(self):
    self.logger.logfile.write(0, "\n\n\n")
    self.logger.log(1, "Starting build of '%s' at %s" % (self.build_id, time.strftime('%Y-%m-%d %X')))
    self.logger.log(5, "Loaded modules: %s" % self.cvars['loaded-modules'])
    self.logger.log(5, "Event list: %s" % [ e.id for e in self.dispatch._top ])
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
  
    # set up base variables
    di = ptr.cvars['distribution-info'] = {}
  
    di['name']              = self.name 
    di['os']                = self.os
    di['version']           = self.version
    di['arch']              = self.arch
    di['type']              = self.type
    di['build_id']          = self.build_id
    di['anaconda-version']  = None
    di['fullname']          = self.fullname
    di['packagepath']       = 'Packages'
    di['webloc']            = self.webloc
  
    for k,v in di.items():
      setattr(ptr, k, v)
  
    # set up other directories
    ptr.LIB_DIR      = self.LIB_DIR
    ptr.CACHE_DIR    = self.CACHE_DIR
    ptr.METADATA_DIR = self.METADATA_DIR 
    ptr.SHARE_DIRS   = self.sharedirs
    ptr.CACHE_MAX_SIZE = self.CACHE_MAX_SIZE
  
    ptr.datfn = self.datfn # dat filename
    ptr.cache_handler = self.cache_handler

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
  moduleid = 'all' 
  def __init__(self, ptr):
    Event.__init__(self,
      id = 'all',
      ptr = ptr,
      version = 1.01,
      properties = CLASS_META,
      suppress_run_message = True,
    )
