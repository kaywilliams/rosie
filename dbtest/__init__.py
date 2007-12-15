import imp
import sys
import time
import unittest

from StringIO import StringIO

from dims import logger
from dims import pps
from dims import xmllib

from dimsbuild.main import Build

from dbtest.config import make_default_config, add_config_section


class TestBuild(Build):
  def __init__(self, conf, *args, **kwargs):
    self.conf = conf
    Build.__init__(self, *args, **kwargs)

  def _get_config(self, options, arguments):
    mcf = pps.Path(options.mainconfigpath or '/etc/dimsbuild.conf')
    if mcf.exists():
      self.mainconfig = xmllib.config.read(mcf)
    else:
      self.mainconfig = xmllib.config.read(StringIO('<dimsbuild/>'))

    self.distroconfig = self.conf


class EventTestCase(unittest.TestCase):
  def __init__(self, conf=None):
    self.conf = conf or make_default_config(self.moduleid)
    if hasattr(self, '_conf'): # can be either a string or a list of strings
      if isinstance(self._conf, str):
        add_config_section(self.conf, self._conf)
      else:
        for sect in self._conf:
          add_config_section(self.conf, sect)
    # make sure an appropriate config section exists
    if not self.conf.pathexists(self.moduleid):
      add_config_section(self.conf, '<%s enabled="true"/>' % self.moduleid)
    # pretend we read from a config file in the modules directory
    self.conf.file = pps.Path(__file__).dirname/'modules/%s' % self.moduleid

    self.event = None
    unittest.TestCase.__init__(self)

    self.parser = None

    self.tb = None

    self._testMethodDoc = self.__class__.__doc__

  def setUp(self):
    self.tb = TestBuild(self.conf, self.options, [], self.parser)
    self.event = self.tb.dispatch._top.get(self.eventid, None)
    self.tb._lock()

  def runTest(self): pass

  def tearDown(self):
    self.tb._unlock()
    del self.tb
    del self.event

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
    self.failIf(pps.Path(path).exists(), "'%s' exists" % path)
  def failUnlessExists(self, path):
    self.failUnless(pps.Path(path).exists(), "'%s' does not exist " % path)

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
    event.setup()
    if not event.skipped:
      if event.forced:
        event.clean()
      if event.check():
        event.run()
        ran = True
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

  def setUp(self):
    pass

  def tearDown(self):
    (pps.Path(__file__).dirname/'modules').listdir('*.dat').rm()

  def run(self, result):
    self.setUp()
    ret = unittest.TestSuite.run(self, result)
    self.tearDown()
    return ret

class EventTestRunner:
  def __init__(self, threshold=1):
    self.logger = make_logger(threshold)

  def run(self, test):
    result = EventTestResult(self.logger)

    starttime = time.time()
    test(result)
    stoptime = time.time()

    if result.failures or result.errors:
      self.logger.log(1, '\n\nERROR/FAILURE SUMMARY')
      result.printErrors()

    self.logger.log(1, result.separator2)
    self.logger.log(1, "ran %d test%s in %.3fs" %
      (result.testsRun, result.testsRun != 1 and 's' or '', stoptime-starttime))
    self.logger.write(1, '\n')

    if not result.wasSuccessful():
      self.logger.write(1, 'FAILED (')
      failed, errored = len(result.failures), len(result.errors)
      if failed:
        self.logger.write(1, 'failures=%d' % failed)
      if errored:
        if failed: self.logger.write(1, ', ')
        self.logger.write(1, 'errors=%d' % errored)
      self.logger.write(1, ')\n')
    else:
      self.logger.write(1, 'OK\n')
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
      self.logger.log(1, test.shortDescription())
    else:
      self.logger._eventid = test.eventid
      self.logger.log(1, test.shortDescription() or str(test), newline=False, format='[%(eventid)s] %(message)s')
      self.logger.write(1, ' ... ')

  def addSuccess(self, test):
    unittest.TestResult.addSuccess(self, test)
    if not isinstance(test, EventTestCaseDummy):
      self.logger.write(1, 'ok\n')

  def addError(self, test, err):
    unittest.TestResult.addError(self, test, err)
    if not isinstance(test, EventTestCaseDummy):
      self.logger.write(1, 'ERROR\n')

  def addFailure(self, test, err):
    unittest.TestResult.addFailure(self, test, err)
    if not isinstance(test, EventTestCaseDummy):
      self.logger.write(1, 'FAIL\n')

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

  def format(self, msg, format=None, **kwargs):
    d = dict(message=msg, eventid=self._eventid, **kwargs)
    if format: d['message'] = format % d
    return self._format % d


LOGFILE = open('test.log', 'w+')

def make_logger(threshold):
  console = logger.Logger(threshold=threshold, file_object=sys.stdout)
  logfile = logger.Logger(threshold=threshold, file_object=LOGFILE)
  return EventTestLogContainer([console, logfile])

def make_suite():
  suite = unittest.TestSuite()

  for module in pps.Path('modules').findpaths(mindepth=1, maxdepth=1):
    if module.basename == '__init__.py': continue
    module = module.replace('.py', '')
    fp = None
    try:
      try:
        fp,p,d = imp.find_module(module.basename, [module.dirname])
      except ImportError:
        continue
      mod = imp.load_module('test-%s' % module.basename, fp, p, d)
    finally:
      fp and fp.close()

    suite.addTest(mod.make_suite())

  return suite

def decorate(testcase, method, prefn=None, postfn=None):
  orig = getattr(testcase, method)

  def decorated(*args, **kwargs):
    prefn and prefn()
    orig(*args, **kwargs)
    postfn and postfn()

  setattr(testcase, method, decorated)
