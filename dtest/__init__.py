#
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
import datetime
import imp
import lxml
import os
import re 
import sys
import time
import unittest

from StringIO import StringIO

from deploy.util import logger
from deploy.util import pps
from deploy.util import repo
from deploy.util import shlib

from deploy.util.rxml import config

from deploy.main import Build, DIST_TAG

BUILD_ROOT = '/tmp/dtest' # location builds are performed
EDITION = 'server'

class TestBuild(Build):
  def __init__(self, conf, options=None, args=None):
    self.conf = conf
    Build.__init__(self, options, args)

  def _get_config(self, options, arguments):
    self.mainconfig = options.mainconfig

  def _setup_cache(self, options):
    self.CACHE_DIR = options.cache_dir
    self.cache_handler = options.cache_handler

  def _get_main_vars(self, *args):
    self.name    = self.conf.getxpath('./main/name/text()')
    self.os      = self.conf.getxpath('./main/os/text()')
    self.version = self.conf.getxpath('./main/version/text()')
    self.arch    = self.conf.getxpath('./main/arch/text()')
    self.id      = self.conf.getxpath('./main/id/text()')

  def _get_definition_path(self, *args):
    self.definition_path = pps.path(self.conf.base)

  def _get_definition(self, options, arguments):
    self.definition = self.conf
    self.definition.xinclude(macros=self.initial_macros, 
                             macro_defaults_file=self.datfile_format)
    self.definition.remove_macros(defaults_file=self.datfile_format)

class EventTestCase(unittest.TestCase):
  def __init__(self, os, version, arch='i386', conf=None):
    self.name = 'dtest-%s' % self.moduleid
    self.os = os 
    self.version = version
    self.arch = arch
    self.id = "%s-%s-%s-%s" % (self.name, self.os, self.version, self.arch)
    # some tests need norm_os prior to initializing the TestBuild object
    self.norm_os = "%s%s" % (DIST_TAG[self.os], self.version)
    # pretend we read from a config file in the modules directory
    self.definition_path = pps.path(__file__).dirname/'modules/%s' % self.moduleid
    # do this before make_default_config()
    self.mainconfig = self.get_mainconfig()

    if conf is not None:
      self.conf = conf
    else:
      self.conf = self._make_default_config()
    self.conf.base = self.definition_path

    self.buildroot = BUILD_ROOT

    # make sure an appropriate config section exists
    if not self.conf.pathexists(self.moduleid):
      self._add_config('<%s enabled="true"/>' % self.moduleid)

    self.event = None
    unittest.TestCase.__init__(self)

    self.tb = None
    self.output = []

    self._testMethodDoc = self.__class__.__doc__

  def get_mainconfig(self):
    mcf = pps.path(self.options.mainconfigpath or '/etc/deploy/dtest.conf')
    if mcf.exists():
      mainconfig = config.parse(mcf).getroot()
    else:
      mainconfig = config.parse(StringIO('<deploy/>').getroot()) 

    # use options to pass mainconfig to TestBuild
    self.options.mainconfig = mainconfig

    return mainconfig

  # hack to get display working properly in centos 5
  def shortDescription(self):
    return self._testMethodDoc

  # config setup
  def _make_default_config(self):
    top = config.Element('definition', attrib={'schema-version': '1.0'})

    main = self._make_main_config()
    if main is not None: top.append(main)

    repos = self._make_repos_config()
    if repos is not None: top.append(repos)

    self.conf = top

    if hasattr(self, '_conf'): # string or list of strings
      if isinstance(self._conf, basestring):
        self._conf = [self._conf]
      for cfg in self._conf:
        self._add_config(cfg)

    return self.conf

  # subclass the following methods to change the default config we make; should
  # return config.ConfigElement object or None

  def _make_main_config(self):
    main = config.Element('main')

    config.Element('name',     text=self.name, parent=main)
    config.Element('os',       text=self.os, parent=main)
    config.Element('version',  text=self.version, parent=main)
    config.Element('arch',     text=self.arch, parent=main)
    config.Element('id',       text=self.id, parent=main) 
    config.Element('fullname', text='%{name} event test', parent=main)
    config.Element('type',     text=getattr(self, '_type', 'system'), 
                               parent=main)

    return main

  def _make_repos_config(self):
    repos = config.fromstring("""
<repos xmlns:xi="http://www.w3.org/2001/XInclude">
<macro id='os'>%(os)s</macro>
<macro id='edition'>%(edition)s</macro>
<macro id='version'>%(version)s</macro>
<macro id='arch'>%(arch)s</macro>
<xi:include href='%(href)s'
            xpointer="xpointer(./repo[@id='%(os)s-%(edition)s-base'])"/>
</repos>
""" % {'os':      self.os, 
       'edition': EDITION,
       'version': self.version, 
       'arch':    self.arch, 
       'href':    pps.path('%{templates-dir}/%{norm-os}/common/repos.xml')})

    return repos

  def _add_config(self, section):
    sect = config.parse(StringIO(section)).getroot()
    for old in self.conf.xpath(sect.tag, []):
      self.conf.remove(old)
    self.conf.append(sect)

  # test suite methods
  def setUp(self):
    self.tb = TestBuild(self.conf, options=self.options, args=[]) 
    self.event = self.tb.dispatch._top.get(self.eventid, None)
    if not self.tb._lock.acquire():
      print "unable to lock (currently running pid is %s: %s)" % (self.tb._lock.path.read_text().strip(), self.tb._lock.path)
      print "current event: '%s'" % self.event.id
      print "test case: %s" % self._testMethodDoc
      print "continuing anyway"

  def runTest(self): pass

  def tearDown(self):
    self.output.append(self.event.METADATA_DIR)
    self.tb._lock.release()
    del self.tb
    del self.event
    del self.conf

  # helper methods
  def clean_all_md(self):
    for event in self.event.getroot():
      self.clean_event_md(event)
  def clean_event_md(self, event=None):
    (event or self.event).mddir.listdir(all=True).rm(recursive=True)

  def execute_predecessors(self, event):
    "run all events prior to this event"
    previous = event.get_previous()
    if previous:
      self.tb.dispatch.execute(until=previous)

  def failIfExists(self, path):
    self.failIf(pps.path(path).exists(), "'%s' exists" % path)
  def failUnlessExists(self, path):
    self.failUnless(pps.path(path).exists(), "'%s' does not exist " % path)

  def failIfRuns(self, event):
    ran = self._runEvent(event)
    if event.diff.handlers: # only events with diff handlers are subject
      diffs = {}
      for id, handler in event.diff.handlers.items():
        if handler.diffdict: diffs[id] = handler.diffdict
      self.failIf(ran, "'%s' event ran:\n%s" % (event.id, diffs))
  def failUnlessRuns(self, event):
    self.failUnless(self._runEvent(event), "'%s' event did not run" % event.id)

  def failUnlessRaises(self, exception, event):
    unittest.TestCase.failUnlessRaises(self, exception, self._runEvent, event)

  def _runEvent(self, event):
    "paired down duplicate of Event.execute()"
    ran = False
    if event.skipped:
      event.setup()
    else:
      if event.forced:
        event.clean()
      event.setup()
      if event.check():
        event.run()
        event.postrun()
        ran = True
    event.clean_eventcache()
    event.apply()
    event.verify()
    return ran

class EventTestCaseDummy(unittest.TestCase):
  "'unittest' for printing out stuff without actually testing"
  def runTest(self): pass

class ModuleTestSuite(unittest.TestSuite):
  "test suite with some custom setup/teardown code"
  separator1 = '='*70
  separator2 = '-'*70

  def __init__(self, modid, tests=()):
    unittest.TestSuite.__init__(self, tests)
    self.modid = modid

    self.output = [] # hack to ensure we can remove all output

  def setUp(self):
    pass

  def tearDown(self):
    (pps.path(__file__).dirname/'modules').listdir('*.dat').rm()
    for dir in self.output:
      dir.rm(recursive=True, force=True)

  def run(self, result):
    self.setUp()
    try:
      for test in self._tests:
        if result.shouldStop:
          break
        test(result)
        try:
          self.output.extend(test.output)
        except:
          pass
      return result
    finally:
      self.tearDown()

class EventTestRunner:
  def __init__(self, logfile, threshold):
    self.logger = make_logger(open(logfile, 'a+'), threshold)

  def run(self, test):
    result = EventTestResult(self.logger)

    starttime = time.time()
    test(result)
    stoptime = time.time()
    result.duration = stoptime - starttime

    if result.failures or result.errors:
      self.logger.log(2, '\n\nERROR/FAILURE SUMMARY')
      result.printErrors()

    self.logger.log(2, result.separator2)
    self.logger.log(2, "ran %d test%s in %s" %
      (result.testsRun,
       result.testsRun != 1 and 's' or '',
       datetime.timedelta(seconds=int(round(result.duration)))))
    self.logger.write(2, '\n')

    if not result.wasSuccessful():
      self.logger.write(2, 'FAILED (')
      failed, errored = len(result.failures), len(result.errors)
      if failed:
        self.logger.write(2, 'failures=%d' % failed)
      if errored:
        if failed: self.logger.write(1, ', ')
        self.logger.write(2, 'errors=%d' % errored)
      self.logger.write(2, ')\n')
    else:
      self.logger.write(2, 'OK\n')
    return result


class EventTestResult(unittest.TestResult):
  separator1 = '='*70
  separator2 = '-'*70

  def __init__(self, logger):
    unittest.TestResult.__init__(self)

    self.logger = logger

  def startTest(self, test):
    unittest.TestResult.startTest(self, test)
    if isinstance(test, EventTestCaseDummy):
      self.logger.log(2, test.shortDescription())
    else:
      self.logger._eventid = test.eventid
      self.logger.log(2, test.shortDescription() or str(test), newline=False, format='[%(eventid)s] %(message)s')
      self.logger.write(2, ' ... ')

  def addSuccess(self, test):
    unittest.TestResult.addSuccess(self, test)
    if not isinstance(test, EventTestCaseDummy):
      self.logger.write(2, 'ok\n')

  def addError(self, test, err):
    unittest.TestResult.addError(self, test, err)
    if not isinstance(test, EventTestCaseDummy):
      self.logger.write(2, 'ERROR\n')

  def addFailure(self, test, err):
    unittest.TestResult.addFailure(self, test, err)
    if not isinstance(test, EventTestCaseDummy):
      self.logger.write(2, 'FAIL\n')

  def printErrors(self):
    self.logger.write(1, '\n')
    self.printErrorList('ERROR', self.errors)
    self.printErrorList('FAIL',  self.failures)

  def printErrorList(self, flavor, errors):
    for test, err in errors:
      self.logger.log(1, self.separator1)
      self.logger.log(1, '[%s] %s: %s' % (test.eventid, flavor, test.shortDescription() or test))
      self.logger.log(1, self.separator2)
      self.logger.log(1, str(err))


class EventTestLogContainer(logger.LogContainer):
  def __init__(self, list=None, threshold=None, default=1, format='%(message)s',):
    if list is None: list = []
    logger.LogContainer.__init__(self, list, threshold, default)
    self._format = format
    self._eventid = None

  def log(self, level, msg, format=None, newline=True, **kwargs):
    msg = self.format(str(msg), format, **kwargs)
    if newline: msg += '\n'
    self.write(level, msg)

  def write(self, level, msg, **kwargs):
    for log_obj in self.list:
      log_obj.write(level, msg, **kwargs)
      log_obj.file_object.flush()

  def format(self, msg, format=None, **kwargs):
    d = dict(message=msg, eventid=self._eventid, **kwargs)
    if format: d['message'] = format % d
    return self._format % d


def make_logger(logfile, threshold):
  console = logger.Logger(threshold=threshold, file_object=sys.stdout)
  logfile = logger.Logger(threshold=2, file_object=logfile) #! write eventhing to file
  return EventTestLogContainer([console, logfile])

def make_suite(os, version, arch='i386', *args, **kwargs):
  suite = unittest.TestSuite()

  for module in pps.path('modules').findpaths(mindepth=1, maxdepth=1):
    if module.basename == '__init__.py': continue
    module = module.abspath()
    modname = module.basename.replace('.py', '')
    fp = None
    try:
      try:
        if module.isdir():
          fp,p,d = imp.find_module('__init__', [module])
        elif module.isfile():
          fp,p,d = imp.find_module(modname, [module.dirname])
        mod = imp.load_module('test-%s' % modname, fp, p, d)
      except ImportError:
        continue
    finally:
      fp and fp.close()

    suite.addTest(mod.make_suite(os, version, arch))

  return suite

def decorate(testcase, method, prefn=None, postfn=None):
  orig = getattr(testcase, method)

  def decorated(*args, **kwargs):
    prefn and prefn()
    orig(*args, **kwargs)
    postfn and postfn()

  setattr(testcase, method, decorated)

def _run_make(dir):
  cwd = os.getcwd()
  os.chdir(dir)
  shlib.execute('/usr/bin/make')
  os.chdir(cwd)

