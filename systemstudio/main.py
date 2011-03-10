#
# Copyright (c) 2011
# Rendition Software, Inc. All rights reserved.
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

Python script defining the Build class, the primary controller for the SystemStudio.
"""

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
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

from systemstudio.util import dispatch
from systemstudio.util import listfmt
from systemstudio.util import lock
from systemstudio.util import pps
from systemstudio.util import rxml
from systemstudio.util import shlib
from systemstudio.util import si

from systemstudio.util import sync
from systemstudio.util.sync import cache
from systemstudio.util.sync import link

from systemstudio.callback  import (SyncCallback, CachedSyncCallback, LinkCallback,
                            SyncCallbackCompressed)
from systemstudio.constants import *
from systemstudio.errors    import SystemStudioErrorHandler, SystemStudioError
from systemstudio.event     import Event, CLASS_META
from systemstudio.logging   import make_log, L0, L1, L2
from systemstudio.validate  import SystemStudioValidationHandler

from systemstudio.event.loader import Loader

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

DEFAULT_TEMP_DIR = pps.path('/tmp/systemstudio')
DEFAULT_CACHE_DIR = pps.path('/var/cache/systemstudio')
DEFAULT_SHARE_DIR = pps.path('/usr/share/systemstudio')
DEFAULT_LOG_FILE = pps.path('/var/log/systemstudio.log')

# map our supported archs to the highest arch in that arch 'class'
ARCH_MAP = {'i386': 'athlon', 'x86_64': 'x86_64'}

# the following chars are allowed in filenames...
FILENAME_REGEX = re.compile('^[a-zA-Z0-9_\-\.]+$')

class Build(SystemStudioErrorHandler, SystemStudioValidationHandler, object):
  """
  Primary build class - framework upon which a custom systemstudio is generated

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

  def __init__(self, options, arguments):
    """
    Initialize a Build object

    Accepts two parameters:
      options:   an  optparse.Options  object  with  the  command  line
                 arguments encountered during command line parsing
      arguments: a list of arguments not processed by the parser

    These parameters are normally passed in from the command-line handler
    ('/usr/bin/systemstudio')
    """

    # set up temporary logger - console only
    self.logger = make_log(options.logthresh)

    # set up configs
    try:
      self._get_config(options, arguments)
    except Exception, e:
      self.logger.log(0, L0(e))
      sys.exit(1)

    # set debug mode
    if options.debug is not None:
      self.debug = options.debug
    elif self.mainconfig.pathexists('/systemstudio/debug'):
      self.debug = self.mainconfig.getbool('/systemstudio/debug', False)
    else:
      self.debug = False

    # set up real logger - console and file
    self.logfile = ( pps.path(options.logfile)
                     or self.appconfig.getpath('/distribution/main/log-file', None)
                     or self.mainconfig.getpath('/systemstudio/log-file', None)
                     or DEFAULT_LOG_FILE ).expand().abspath()
    try:
      self.logger = make_log(options.logthresh, self.logfile)
    except IOError, e:
      self.logger.log(0, L0("Error opening log file for writing: %s" % e))
      if self.debug: raise
      sys.exit(1)

    # set up event superclass so that it contains good default values
    self._seed_event_defaults(options)

    # change working dir to config dir so relative paths expand properly
    os.chdir(self.appconfig.file.dirname)

    # set up import_dirs
    import_dirs = self._compute_import_dirs(options)

    # set up lists of enabled and disabled modules
    enabled, disabled = self._compute_modules(options)

    load_extensions = False
    if options.list_modules:
      # remove all disabled modules - we want to see them all
      disabled = ['__init__']
      # load all extension modules explicitly
      load_extensions = True

    # load all enabled modules, register events, set up dispatcher
    loader = Loader(top = AllEvent(), api_ver = API_VERSION,
                    enabled = enabled, disabled = disabled,
                    load_extensions = load_extensions)

    try:
      self.dispatch = dispatch.Dispatch(
                        loader.load(import_dirs, prefix='systemstudio/modules')
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
      Event.logger.log(0, L0("Error loading core systemstudio files: %s" % e))
      if self.debug: raise
      sys.exit(1)

    # list modules, if requested
    if options.list_modules:
      self._pprint_modules(loader)
      sys.exit()

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
    Event.cache_handler.cache_dir.mkdirs()

    # perform validation, if not specified otherwise
    if not options.no_validate:
      self.validate_configs()
      if options.validate_only:
        print self.appconfig
        sys.exit()

    # set up locking
    self._lock = lock.Lock(Event.cache_handler.cache_dir/'systemstudio.pid')

  def main(self):
    "Build a system distribution"
    if self._lock.acquire():
      self._log_header()
      try:
        try:
          self.dispatch.execute(until=None)
        except (SystemStudioError, Exception, KeyboardInterrupt), e:
          self._handle_Exception(e)
      finally:
        self._lock.release()
      DEFAULT_TEMP_DIR.rm(recursive=True, force=True) # clean up temp dir
      self._log_footer()
    else:
      self.logger.log(0, L0("Another instance of systemstudio (pid %d) is already "
                            "running" % self._lock._readlock()[0]))
      sys.exit()

  def _get_config(self, options, arguments):
    """
    Gets the main config and system definition based on option values.  Main
    config file is optional; if not found, merely uses a set of default
    values.  Distribution config is required, except in the event that the '-h' or
    '--help' argument was given on the command line, in which case the system distribution
    config file can be omitted or not exist.  (This previous allowance is so
    that a user can type `systemstudio -h` on the command line without giving
    the '-c' option.)
    """
    mcp = pps.path(options.mainconfigpath).expand().abspath()
    dcp = pps.path(arguments[0]).expand().abspath()
    if mcp and mcp.exists():
      self.logger.log(4, "Reading '%s'" % mcp)
      mc = rxml.config.read(mcp)
    else:
      self.logger.log(4, "No main config file found at '%s'. Using default settings" % mcp)
      mc = rxml.config.fromstring('<systemstudio/>')

    if not dcp.exists():
      raise rxml.errors.ConfigError("No system definition file found at '%s'" % dcp)

    self.logger.log(3, "Reading '%s'" % dcp)
    dc = rxml.config.read(dcp)

    self.mainconfig = mc
    self.appconfig = dc

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
    import_dirs = [ x.expand().abspath() for x in \
      self.mainconfig.getpaths('/systemstudio/lib-path', []) ]

    if options.libpath:
      import_dirs = [ pps.path(x).expand().abspath() for x in options.libpath ] + import_dirs
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(pps.path(dir))

    return import_dirs

  def _compute_modules(self, options):
    """
    Compute a list of modules systemstudio should not load.  Disabling takes priorty
    over enabling.

    options      : an optparse.Values instance containing the result of
                   parsing command line options
    """
    enabled  = set(options.enabled_modules)
    disabled = set(options.disabled_modules)

    # enable/disable modules from app config
    for module in self.appconfig.xpath('/distribution/*'):
      if module.tag == 'main': continue # main isn't a module
      if not module.getbool('@enabled', 'True'):
        disabled.add(module.tag)
      else:
        enabled.add(module.tag)

    # enable/disable modules from main config
    for module in self.mainconfig.xpath('/systemstudio/enable-module', []):
      enabled.add(module.text)
    for module in self.mainconfig.xpath('/systemstudio/disable-module', []):
      disabled.add(module.text)

    disabled.add('__init__') # hack, kinda; these are loaded automatically

    return enabled, disabled

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
    Event._config    = self.appconfig

    # set up base variables
    di = Event.cvars['distribution-info'] = {}
    qstr = '/distribution/main/%s/text()'

    di['name']         = Event._config.get(qstr % 'name')
    di['version']      = Event._config.get(qstr % 'version')
    di['arch']         = ARCH_MAP[Event._config.get(qstr % 'arch', 'i386')]
    di['basearch']     = getBaseArch(di['arch'])
    di['distributionid']  = Event._config.get(qstr % 'id',
                          '%s-%s-%s' % (di['name'],
                                        di['version'],
                                        di['basearch']))
    di['anaconda-version'] = None
    di['fullname']     = Event._config.get(qstr % 'fullname', di['name'])
    di['packagepath']  = 'Packages'
    di['webloc']       = Event._config.get(qstr % 'bug-url', 'No bug url provided')

    for k,v in di.items():
      setattr(Event, k, v)

    # validate name, version, and distributionid to ensure they don't have
    # invalid characters
    for check in ['name', 'version', 'distributionid']:
      if not FILENAME_REGEX.match(di[check]):
        raise RuntimeError("Invalid value '%s' for <%s> element in <main>; "
          "accepted characters are a-z, A-Z, 0-9, _, ., and -."
          % (di[check], check))

    # make distributionid available to external programs via the Build object
    Build.distributionid = di['distributionid']

    # set up other directories
    Event.CACHE_DIR    = self.mainconfig.getpath('/systemstudio/cache/path',
                           DEFAULT_CACHE_DIR).expand().abspath()
    Event.TEMP_DIR     = DEFAULT_TEMP_DIR
    Event.METADATA_DIR = Event.CACHE_DIR  / di['distributionid']

    sharedirs = [ DEFAULT_SHARE_DIR ]
    sharedirs.extend(reversed([ x.expand().abspath()
      for x in self.mainconfig.getpaths('/systemstudio/share-path', []) ]))
    sharedirs.extend(reversed([ pps.path(x).expand().abspath()
      for x in options.sharepath ]))

    # reverse the order so we get cli options, then config, then defaults
    Event.SHARE_DIRS = [ x for x in reversed(sharedirs) ]
    for d in Event.SHARE_DIRS:
      if not d==DEFAULT_SHARE_DIR and not d.isdir():
        raise RuntimeError("The specified share-path '%s' does not exist." %d)

    cache_max_size = self.mainconfig.get('/systemstudio/cache/max-size/text()', '30GB')
    if cache_max_size.isdigit():
      cache_max_size = '%sGB' % cache_max_size
    Event.CACHE_MAX_SIZE = si.parse(cache_max_size)

    Event.cache_handler = cache.CachedSyncHandler(
                            cache_dir = Event.CACHE_DIR / '.cache',
                            cache_max_size = Event.CACHE_MAX_SIZE)
    Event.copy_handler = sync.CopyHandler()
    Event.link_handler = link.LinkHandler(allow_xdev=True)

    Event.copy_callback  = SyncCallback(Event.logger, Event.METADATA_DIR)
    Event.cache_callback = CachedSyncCallback(Event.logger, Event.METADATA_DIR)
    Event.link_callback  = LinkCallback(Event.logger, Event.METADATA_DIR)
    Event.copy_callback_compressed = SyncCallbackCompressed(
                                     Event.logger, Event.METADATA_DIR)

    selinux_enabled = False
    try:
      selinux_enabled = shlib.execute('/usr/sbin/getenforce')[0] != 'Disabled'
    except:
      pass
    Event.cvars['selinux-enabled'] = selinux_enabled

  def _pprint_modules(self, loader):
    width = 74

    modgrps = {}
    for modid, module in loader.modules.items():
      grp = module.MODULE_INFO.get('group')
      if grp and module.MODULE_INFO.get('description') is not None:
        modgrps.setdefault(grp, []).append(modid)

    longest = 0
    sep = ' : '
    for modid in loader.modules:
      longest = max(longest, len(modid))
    s = '%%-%ds' % longest

    lfmt = listfmt.ListFormatter(start='including ', sep=', ', last=' and ', end=' modules')
    twrp = textwrap.TextWrapper(subsequent_indent = ' '*(longest+len(sep)), width=width)

    print "\nFollowing is a list of modules by group:"

    for grp in sorted(modgrps.keys()):
      if loader.modules.has_key(grp):
        if loader.modules[grp].MODULE_INFO.get('description') is None:
          continue
        r = (s % grp, sep, loader.modules[grp].MODULE_INFO.get('description', ''))
      else:
        continue
      print ""
      print twrp.fill('%s%s%s' % r)
      print "="*width

      for modid in sorted(modgrps[grp]):
        if loader.modules.has_key(modid):
          if loader.modules[modid].MODULE_INFO.get('description') is None:
            continue
          r = (s % modid, sep, loader.modules[modid].MODULE_INFO.get('description', ''))
        else:
          r = (s % modid, '', '')
        print twrp.fill('%s%s%s' % r)

    r = (s % 'none', sep, 'modules not associated with a group')
    print ""
    print twrp.fill('%s%s%s' % r)
    print "="*width
    r = (s % 'none', sep, 'modules not associated with a group')
    for modid in sorted([ x for x in loader.modules if
                              x not in modgrps.keys() and
                              not loader.modules[x].MODULE_INFO.get('group')]):
      if loader.modules.has_key(modid):
        if loader.modules[modid].MODULE_INFO.get('description') is None:
          continue
        r = (s % modid, sep, loader.modules[modid].MODULE_INFO.get('description', ''))
      else:
        r = (s % modid, '', '')
      print twrp.fill('%s%s%s' % r)

  def _log_header(self):
    Event.logger.logfile.write(0, "\n\n\n")
    Event.logger.log(1, "Starting build of '%s' at %s" % (Event.distributionid, time.strftime('%Y-%m-%d %X')))
    Event.logger.log(4, "Loaded modules: %s" % Event.cvars['loaded-modules'])
    Event.logger.log(4, "Event list: %s" % [ e.id for e in self.dispatch._top ])
  def _log_footer(self):
    Event.logger.log(1, "Build complete at %s" % time.strftime('%Y-%m-%d %X'))


class CvarsDict(dict):
  def __getitem__(self, key):
    return self.get(key, None)


class AllEvent(Event):
  "Top level event that is the ancestor of all other events.  Changing this "
  "event's version will cause all events to automatically run."
  moduleid = None
  def __init__(self):
    Event.__init__(self,
      id = 'all',
      version = 1,
      properties = CLASS_META,
      suppress_run_message = True
    )
