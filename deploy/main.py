
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
from deploy.util.pps.Path.error   import OfflinePathError
from deploy.util.pps.cache        import CacheHandler
from deploy.util.pps.search_paths import SearchPathsHandler

from deploy.util import sync

from deploy.callback  import (DeployCliCallback, 
                              SyncCallback, CachedCopyCallback,
                              LinkCallback, SyncCallbackCompressed)
from deploy.constants import *
from deploy.dlogging  import make_log, L0, L1, L2
from deploy.errors    import (DeployCliErrorHandler,
                              DeployEventErrorHandler, 
                              DeployEventError,
                              DeployError,
                              InvalidOptionError,
                              InvalidMainConfigPathError,)
from deploy.options   import DeployOptionParser
from deploy.event     import Event, CLASS_META
from deploy.validate  import (DeployValidationHandler,
                                    InvalidEventError)

from deploy.event.loader import Loader

from rpmUtils.arch import getArchList

# RPMS we need to check for
# createrepo
# anaconda-runtime
# python-devel
# syslinux
# python-setuptools

API_VERSION = 5.0

DEFAULT_CACHE_DIR = pps.path('/var/cache/deploy')
DEFAULT_LOCAL_ROOT = pps.path('/var/lib/deploy')
DEFAULT_SHARE_DIR = pps.path('/usr/share/deploy')
DEFAULT_TEMPLATE_DIRS = [ pps.path('/usr/share/deploy/templates') ]
DEFAULT_LOG_FILE = pps.path('/var/log/deploy.log')

SUPPORTED = ['centos-6-i386', 'centos-6-x86_64', 
             'rhel-6-i386', 'rhel-6-x86_64',
             'centos-7-x86_64', 'rhel-7-x86_64',
             'fedora-21-x86_64']

DIST_TAG = { 
  'centos': 'el',
  'rhel'  : 'el',
  'fedora': 'fc',
  }

# map our supported archs to the highest arch in that arch 'class'
ARCH_MAP = {'i386': 'athlon', 'x86_64': 'x86_64'}


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

  def __init__(self, options, arguments, callback=DeployCliCallback(),
                     error_handler=DeployCliErrorHandler):
    """
    Initialize a Build object

    Accepts three parameters:
      options:   an optparse.Options  object  with  the  command  line
                 arguments encountered during command line parsing; a
                 string or list may also be provided - deploy will attempt
                 to convert to an optparse.Options object
      arguments: a list of arguments not processed by the parser, specifically
                 must contain the definition
      callback:  a callback object providing set_debug and set_logger functions
      error_handler: a function to handle errors; errors raised normally
                 if set to none

    These parameters are normally passed in from the command-line handler
    ('/usr/bin/deploy')
    """
    # set arguments - convert to list as needed
    if not hasattr(arguments, '__iter__'): arguments = [arguments]

    # set options - convert to optparse.Options as needed
    if not hasattr(options, '__dict__'):
      if not hasattr(options, '__iter__'): options = options.split()
      options = DeployOptionParser().parse_args(args=options)[0]

    # set callback
    self.callback = callback

    # set error handler
    self.error_handler = error_handler

    try:
      # set up temporary logger - console only
      self.logger = make_log(options.logthresh)
      if self.callback: self.callback.set_logger(self.logger)

      # set initial debug value from options
      self.debug = False
      if options.debug is not None:
        self.debug = options.debug
      if self.callback: self.callback.set_debug(self.debug)

      # set up configs
      try:
        self._get_config(options, arguments)
        self._setup_cache(options)
        self._get_definition_path(arguments)
        self._get_data_root(options)
        self._get_templates_dir()
        self._get_main_vars(options)
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
      if self.callback: self.callback.set_debug(self.debug)

      # set up initial variables
      qstr = '/*/main/%s/text()'

      self.type   = self.definition.getxpath(qstr % 'type', 'system')

      # set data_dir
      self._get_data_dir(options)

      # set up real logger - console and file, unless provided as init arg
      self.logfile = ( pps.path(options.logfile)
                       or self.definition.getpath(
                          '/*/main/log-file/text()', None)
                       or self.mainconfig.getpath(
                          '/deploy/log-file/text()', None)
                       or DEFAULT_LOG_FILE ).expand().abspath()
      self.logfile.exists() or self.logfile.touch()
      self.logfile.chmod(0700)
      self.logfile.chown(0,0)

      try:
        self.logger = make_log(options.logthresh, self.logfile)
      except IOError, e:
        raise DeployError("Error opening log file for writing: %s" % e)
      if self.callback: self.callback.set_logger(self.logger)

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

    except BaseException, e:
      if self.error_handler:
        self.error_handler(error=e, callback=self.callback)
      else: raise

  def main(self):
    "Build a repository"
    try:
      if self._lock.acquire():
        self._log_header()
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
    except BaseException, e:
      if self.error_handler:
        self.error_handler(error=e, callback=self.callback)
      else: raise

  def _get_config(self, options, arguments):
    """
    Gets the deploy config based on option values. The deploy
    config file is optional; if not found, merely uses a set of default values.
    """
    cp = pps.path(options.mainconfigpath).expand().abspath()
    if cp and cp.exists():
      self.logger.log(4, "Reading '%s'" % cp)
      try:
        mc = rxml.config.parse(cp).getroot()
      except (IOError, rxml.errors.XmlSyntaxError), e:
        raise DeployError("Error reading deploy configuration: %s" % e)
    else:
      self.logger.log(4, "No deploy config file found at '%s'. Using default settings" % cp)
      mc = rxml.config.fromstring('<deploy/>')

    self.mainconfig = mc

  def _setup_cache(self, options):
    self.CACHE_DIR    = self._get_mainconfig_paths('cache/path') or \
                        DEFAULT_CACHE_DIR
    self.CACHE_DIR.exists() or self.CACHE_DIR.mkdir()
    self.CACHE_DIR.chmod(0700)
    self.CACHE_DIR.chown(0,0)

    cache_max_size = self.mainconfig.getxpath('/deploy/cache/max-size/text()',
                                              '30GB')
    if cache_max_size.isdigit():
      cache_max_size = '%sGB' % cache_max_size

    self.cache_handler = CacheHandler(cache_dir = self.CACHE_DIR / '.cache',
                               cache_max_size = si.parse(cache_max_size),
                               offline = self.mainconfig.getxpath(
                                         '/deploy/offline/text()', 
                                          options.offline))

  def _get_definition_path(self, arguments):
    self.definition_path = pps.path(arguments[0]).expand().abspath()
    if not self.definition_path.exists():
      raise rxml.errors.XmlError("No definition found at '%s'" % 
                                 self.definition_path)

  def _get_data_root(self, options):
    self.data_root = (pps.path(options.data_root) or 
                      pps.path(self.definition_path).dirname)
    self.data_root.exists() or self.data_root.mkdir()
    self.data_root.chown(0,0)
    self.data_root.chmod(0700)

    # Specify datfile filename format. The datfile is used for
    # storing two types of data: macro default values and event 
    # generated data (e.g. rpm revision numbers). Set the filename
    # format up outside of the get_definition method so that subclass
    # applications (dtest, srpmbuild) can access it easily.
    self.datfile_format = ('%s/%%s.dat/%%s.dat' % self.data_root,
                          ['./main/id/text()', './main/id/text()'])

  def _get_templates_dir(self):
    self.template_dirs = self._get_mainconfig_paths('templates-path') 
    self.template_dirs.extend(DEFAULT_TEMPLATE_DIRS)

    self.search_paths_handler = SearchPathsHandler({
                                '%{templates-dir}': self.template_dirs 
                                })

  def _get_main_vars(self, options):
    # read definition one time without processing includes or script macros to
    # get name, os, version, arch and id elems. this lets us resolve norm_os
    # early and provide it as a global macro
    try:
      definition = rxml.config.parse(self.definition_path, 
                                     resolve_macros=True,
                                     ignore_script_macros=True,
                                     macros=get_initial_macros(options),
                                     ).getroot()
    except (IOError, rxml.errors.XmlSyntaxError), e:
      raise DeployError("Error reading definition: %s" % e)

    for elem in ['name', 'os', 'version', 'arch', 'id']:
      try:
        if elem == 'id': varname = 'build_id'
        else: varname = elem
        exec ("self.%s = definition.getxpath('./main/%s/text()')" 
              % (varname, elem))
      except rxml.errors.XmlPathError, e:
        msg = ("ERROR: Validation of %s failed. Missing required 'main/%s' "
               "element." % (definition.getroot().getbase(), elem))
        raise DeployError(msg)

    # validate distribution
    if not '%s-%s-%s' % (self.os, self.version, self.arch) in SUPPORTED:
      msg = ("ERROR: The specified operating system '%s-%s-%s' is not "
             "supported. Supported operating systems are %s." % 
             (self.os, self.version, self.arch, SUPPORTED))
      raise DeployError(msg)

  def _get_initial_macros(self, options):
    # setup global macros using values from options, if provided 
    map = get_initial_macros(options)

    map.setdefault('%{name}',    self.name)
    map.setdefault('%{os}',      self.os)
    map.setdefault('%{version}', self.version)
    map.setdefault('%{arch}',    self.arch)
    map.setdefault('%{id}',      self.build_id)

    self.norm_os = '%s%s' % (DIST_TAG[self.os], self.version)
    map.setdefault('%{norm-os}', self.norm_os)

    map.setdefault('%{templates-dir}', rxml.tree.resolve_search_path_macro)
    map.setdefault('%{definition-dir}', pps.path(self.definition_path).dirname)

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

    try:
      dt = rxml.config.parse(self.definition_path, include=True,
                             macros=self.initial_macros,
                             remove_macros=True, 
                             macro_defaults_file=self.datfile_format)
    except (rxml.errors.MacroDefaultsFileXmlPathError, 
            rxml.errors.MacroDefaultsFileNameUnresolved):
      raise DeployError("""
ERROR: Unable to resolve the main/id element. This can be caused by one of two
issues:

* The element is missing from the definition.
* The element contains one or more macro placeholders that cannot be resolved
  prior to performing xinclusion. If this is the case you will need to
  restructure the main/id element to remove reliance on included content.

See the Deploy Definition File Reference for more information on the main/id
element.

The definition file is located at %s.
""" % self.definition_path)
    except (IOError, rxml.errors.XmlSyntaxError), e:
      raise DeployError("Error reading definition: %s" % e)

    self.definition = dt.getroot()

  def _get_data_dir(self, options):
    # setup data-dir and data file name
    self.datfn = self.definition.get_macro_defaults_file(self.datfile_format)

    self.data_dir = self.datfn.dirname

    # if data dir doesn't exists, move legacy data_dir, if exists
    if not self.data_dir and self.data_dir.endswith(".dat"):
      legacy_data_dir = self.data_dir[:-len(".dat")]
      if (legacy_data_dir / self.datfn.basename).exists():
        legacy_data_dir.move(self.data_dir)

    self.data_dir.exists() or self.data_dir.mkdir()
    self.data_dir.chown(0,0)
    self.data_dir.chmod(0700)

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
    import_dirs = self._get_mainconfig_paths('lib-path')

    if options.libpath:
      import_dirs = [ pps.path(x).expand().abspath() for x in options.libpath ] + import_dirs
    for dir in sys.path:
      if dir not in import_dirs:
        import_dirs.append(pps.path(dir))

    return import_dirs

  def _compute_modules(self, options):
    """
    Compute a list of modules deploy should not load. Order of precedence is
    options, definition, deploy config

    options      : an optparse.Values instance containing the result of
                   parsing command line options
    """
    enabled  = set()
    disabled = set()

    # enable/disable modules from deploy config
    for module in self.mainconfig.xpath('/deploy/enable-module', []):
      enabled.add(module.text)
    for module in self.mainconfig.xpath('/deploy/disable-module', []):
      disabled.add(module.text)

    # enable/disable modules from definition 
    for module in self.definition.xpath('/*/*'):
      if module.tag == 'main': continue # main isn't a module
      if not module.getbool('@enabled', 'True'):
        disabled.add(module.tag)
      else:
        enabled.add(module.tag)

    # enable/disable modules from options
    for module in options.enabled_modules:
      enabled.add(module)
      disabled.remove(module)
    for module in options.disabled_modules:
      disabled.add(module)

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
    self.bugurl      = self.definition.getxpath(qstr % 'bug-url', 
                                                  'No bug url provided')

    # set up share directories
    sharedirs = [ DEFAULT_SHARE_DIR ]
    sharedirs.extend(reversed(self._get_mainconfig_paths('share-path')))
    sharedirs.extend(reversed([ pps.path(x).expand().abspath()
      for x in options.sharepath ]))

    # reverse the order so we get cli options, then config, then defaults
    self.sharedirs = [ x for x in reversed(sharedirs) ]
    assert self.sharedirs
    for d in self.sharedirs:
      if not d==DEFAULT_SHARE_DIR and not d.isdir():
        raise DeployError("ERROR: The specified share-path '%s' does not "
                          "exist." %d)

    # set up cache options
    self.METADATA_DIR = self.CACHE_DIR  / (self.type + 's') / self.build_id
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

    # set up root paths for local data
    self.LOCAL_ROOT = pps.path(options.local_root or DEFAULT_LOCAL_ROOT)

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
    di['validarchs']        = getArchList(ARCH_MAP[self.arch])
    di['norm_os']           = self.norm_os
    di['type']              = self.type
    di['build_id']          = self.build_id
    di['anaconda-version']  = None
    di['fullname']          = self.fullname
    di['packagepath']       = 'Packages'
    di['bugurl']            = self.bugurl
  
    for k,v in di.items():
      setattr(ptr, k, v)
  
    # set up other directories
    ptr.CACHE_DIR    = self.CACHE_DIR
    ptr.LOCAL_ROOT     = self.LOCAL_ROOT
    ptr.METADATA_DIR = self.METADATA_DIR 
    ptr.SHARE_DIRS   = self.sharedirs
    ptr.TEMPLATE_DIRS  = self.template_dirs # needed by srpmbuild

    ptr.datfn         = self.datfn # dat filename
    ptr.cache_handler = self.cache_handler

    ptr.copy_callback  = self.copy_callback
    ptr.cache_callback = self.cache_callback
    ptr.link_callback  = self.link_callback
    ptr.copy_callback_compressed = self.copy_callback_compressed

  def _get_mainconfig_paths(self, tag):
    paths = []
    for elem in self.mainconfig.xpath('./%s' % tag, []):
      d = elem.getpath('./text()', None)
      if not d:
        msg = "No path was specified."
        raise InvalidMainConfigPathError(tag, self.mainconfig.base, msg, elem)
      d.expand().abspath()
      if not d.isdir():
        msg = "The specified path does not exist."
        raise InvalidMainConfigPathError(tag, self.mainconfig.base, msg, elem)
      paths.append(d)

    return paths

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

##### Helper Methods #####
def get_initial_macros(options):
  # get macros using values from options 
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

  return map
