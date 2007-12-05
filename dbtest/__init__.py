import imp
import sys
import time
import unittest

from StringIO import StringIO

from dims import logger
from dims import pps
from dims import xmllib

from dimsbuild.main import Build


class TestBuild(Build):
  def __init__(self, conf, *args, **kwargs):
    self.conf = conf
    Build.__init__(self, *args, **kwargs)

  def _get_config(self, options):
    mcf = pps.Path(options.mainconfigpath or '/etc/dimsbuild.conf')
    if mcf.exists():
      self.mainconfig = xmllib.config.read(mcf)
    else:
      self.mainconfig = xmllib.config.read(StringIO('<dimsbuild/>'))

    self.distroconfig = xmllib.config.read(self.conf)


class EventTestCase(unittest.TestCase):
  def __init__(self, eventid, conf):
    self.eventid = eventid
    self.conf = conf

    self.event = None
    unittest.TestCase.__init__(self)

    self.parser = None

    self.tb = None

    self._testMethodDoc = self.__class__.__doc__

  def setUp(self):
    self.tb = TestBuild(self.conf, self.options, self.parser)
    self.event = self.tb.dispatch._top.get(self.eventid)
    self.tb._lock()

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

  for module in pps.Path('modules').findpaths(mindepth=1, maxdepth=1,
                                              type=pps.constants.TYPE_DIR):
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
