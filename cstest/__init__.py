#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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
import sys
import time
import unittest

from StringIO import StringIO

from centosstudio.util import logger
from centosstudio.util import pps
from centosstudio.util import repo
from centosstudio.util import shlib

from centosstudio.util.rxml import config

from centosstudio.main import Build

BUILD_ROOT = '/tmp/cstest' # location builds are performed

class TestBuild(Build):
  def __init__(self, conf, *args, **kwargs):
    self.conf = conf
    Build.__init__(self, *args, **kwargs)

  def _get_config(self, options, arguments):
    mcf = pps.path(options.mainconfigpath or '/etc/centosstudio/cstest.conf')
    if mcf.exists():
      self.mainconfig = config.parse(mcf).getroot()
    else:
      self.mainconfig = config.parse(StringIO('<centosstudio/>')).getroot()

    # set the cache dir
    p = config.uElement('cache', parent=self.mainconfig)
    config.uElement('path', parent=p).text = BUILD_ROOT

  def _get_definition(self, options, arguments):
    self.definition = self.conf
    self.definitiontree = lxml.etree.ElementTree(self.conf)

class EventTestCase(unittest.TestCase):
  def __init__(self, distro, version, arch='i386', conf=None):
    self.distro = distro
    self.version = version
    self.arch = arch
    self.conf = conf or self._make_default_config()
    self.buildroot = BUILD_ROOT

    # make sure an appropriate config section exists
    if not self.conf.pathexists(self.moduleid):
      self._add_config('<%s enabled="true"/>' % self.moduleid)
    # pretend we read from a config file in the modules directory
    self.conf.file = pps.path(__file__).dirname/'modules/%s' % self.moduleid

    self.event = None
    unittest.TestCase.__init__(self)

    self.tb = None
    self.output = []

    self._testMethodDoc = self.__class__.__doc__

  # hack to get display working properly in centos 5
  def shortDescription(self):
    return self._testMethodDoc

  # config setup
  def _make_default_config(self):
    top = config.Element('solution', attrs={'schema-version': '1.0'})

    main = self._make_main_config()
    if main is not None: top.append(main)

    repos = self._make_repos_config()
    if repos is not None: top.append(repos)

    config_rpm  = self._make_config_rpm_config()
    if config_rpm is not None: top.append(config_rpm)

    gpgcheck = self._make_gpgcheck_config()
    if gpgcheck is not None: top.append(gpgcheck)

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

    config.Element('fullname', text='%s event test' % self.moduleid, parent=main)
    config.Element('name',     text='test-%s' % self.moduleid, parent=main)
    config.Element('version',  text=self.version, parent=main)
    config.Element('arch',     text=self.arch, parent=main)

    return main

  def _make_repos_config(self):
    repos = config.Element('repos')

    base = repo.getDefaultRepoById('base', distro=self.distro,
                                           version=self.version,
                                           arch=self.arch,
                                           include_baseurl=True,
                                           baseurl='http://www.renditionsoftware.com/mirrors/%s' % self.distro)
    base.update({'mirrorlist': None, 'gpgkey': None, 'gpgcheck': 'no'})

    repos.append(base.toxml())

    return repos

  def _make_config_rpm_config(self):
    config_rpm = config.Element('config-rpm')
    gpgsign = config.Element('gpgsign', parent=config_rpm)
    config.Element('public', parent=gpgsign, text=PUBKEY)
    config.Element('secret', parent=gpgsign, text=SECKEY)

    return config_rpm

  def _make_gpgcheck_config(self):
    gpgcheck = config.Element('gpgcheck', attrs={'enabled': 'false'})

    return gpgcheck

  def _add_config(self, section):
    sect = config.parse(StringIO(section)).getroot()
    for old in self.conf.xpath(sect.tag, []):
      self.conf.remove(old)
    self.conf.append(sect)

  # test suite methods
  def setUp(self):
    self.tb = TestBuild(self.conf, self.options, [])
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

def make_suite(distro, version, arch='i386', *args, **kwargs):
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

    suite.addTest(mod.make_suite(distro, version, arch))

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
  shlib.execute('make')
  os.chdir(cwd)

PUBKEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQGiBE7iLHkRBACbHdCzgO5Jac4LRbQwKoX+1ltYHrvvc/WsnhuPN5HXhvkPTA+/
rbsCxm8oqzP5puu7rimcnZkHN7pN/8uKj5Vd7EbaVNSWUg7rfhDlxg/KxDAnXPuI
JBhER92JfU0y5D1SOb4SmSJ32E79zrDVFt0XFlOP6biwFS/RGHRJxzjGlwCgnOcN
AYveV6pXd8Ec9OX6Lea+46sD/289sU6VeSg9KruXM67LjDei/P8aDAGsABdhq57F
L7eOcWewZ0UZDQh1zSB+r0DoWF6rpj7oQ/yRWoHWXgFfUX8tL5AV7HuNmsxAfvy/
/xBs8YVgBxieeiWrBGxcBQRdXZDSSOz2WYExir5y4/ehn3Upn5WKeUqkP5uAsQkB
XFOyA/wOOd4azDKd0uouLgluJbqYMSlRDoigNbHWVPAM3PvZdusgzP2JO91IxCHD
JeCpZWgfN29g8py66PkXg7EfsisQqVO3/42me96Tqb/77Y8kSbubWQ4uVQd5YB8z
0sGT71S6NrAnhqyqs7toMjUGO5JuMfnP/hgITk967nV5jZowX7QQdGVzdCBzaWdu
aW5nIGtleYhgBBMRAgAgBQJO4ix5AhsjBgsJCAcDAgQVAggDBBYCAwECHgECF4AA
CgkQyubdJwqXVrONfQCfUS5Qb14tm2ADjxLoZRuYtEpn9WsAoJwnvOfR7XE/Qjqq
s6JooAwdguR6uQENBE7iLHoQBACvveBthapADqBic6ijcQbt1Hb6E/9HAwxubRpj
yl0g8uC1ZxfcQKJ1GT983Bx/okvP73olKOxV1xnlpT7DV+6EYucIGVyW55mrxI3H
P7o1Ox1wvh7fP/pm6Yf//OLF9lFUh3h0/mYziqAaf0L/Vm3aWu9Hl02IJToVifAC
GemE7wADBQQAovTMQ5k8RG1k5jCUqRV280FKInE24M/75YbNXwdTkGfp9pl1ceNJ
1vhlZg3JuHnZ0uw0p3la7WUCut0afy7vCRQPD4g8E57vfBFzOpiifXbEP5VHa37e
hY3hoknv0N3UP7EjWxUoifSi1VsV8WMHcJVxKgu6//oXsHQ6GSypR1aISQQYEQIA
CQUCTuIsegIbDAAKCRDK5t0nCpdWs0DuAKCXthQjeX5H4DL9sZUkxk+k4wiHtgCf
TBefZqqYtL+kacCEgCIYH2Fhm0I=
=9xNj
-----END PGP PUBLIC KEY BLOCK-----"""

SECKEY = """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQG7BE7iLHkRBACbHdCzgO5Jac4LRbQwKoX+1ltYHrvvc/WsnhuPN5HXhvkPTA+/
rbsCxm8oqzP5puu7rimcnZkHN7pN/8uKj5Vd7EbaVNSWUg7rfhDlxg/KxDAnXPuI
JBhER92JfU0y5D1SOb4SmSJ32E79zrDVFt0XFlOP6biwFS/RGHRJxzjGlwCgnOcN
AYveV6pXd8Ec9OX6Lea+46sD/289sU6VeSg9KruXM67LjDei/P8aDAGsABdhq57F
L7eOcWewZ0UZDQh1zSB+r0DoWF6rpj7oQ/yRWoHWXgFfUX8tL5AV7HuNmsxAfvy/
/xBs8YVgBxieeiWrBGxcBQRdXZDSSOz2WYExir5y4/ehn3Upn5WKeUqkP5uAsQkB
XFOyA/wOOd4azDKd0uouLgluJbqYMSlRDoigNbHWVPAM3PvZdusgzP2JO91IxCHD
JeCpZWgfN29g8py66PkXg7EfsisQqVO3/42me96Tqb/77Y8kSbubWQ4uVQd5YB8z
0sGT71S6NrAnhqyqs7toMjUGO5JuMfnP/hgITk967nV5jZowXwAAnA12xL8lKygY
avXfoZC4hAHepi0VCaS0EHRlc3Qgc2lnbmluZyBrZXmIYAQTEQIAIAUCTuIseQIb
IwYLCQgHAwIEFQIIAwQWAgMBAh4BAheAAAoJEMrm3ScKl1azjX0An1EuUG9eLZtg
A48S6GUbmLRKZ/VrAKCcJ7zn0e1xP0I6qrOiaKAMHYLkep0BMgRO4ix6EAQAr73g
bYWqQA6gYnOoo3EG7dR2+hP/RwMMbm0aY8pdIPLgtWcX3ECidRk/fNwcf6JLz+96
JSjsVdcZ5aU+w1fuhGLnCBlclueZq8SNxz+6NTsdcL4e3z/6ZumH//zixfZRVId4
dP5mM4qgGn9C/1Zt2lrvR5dNiCU6FYnwAhnphO8AAwUEAKL0zEOZPERtZOYwlKkV
dvNBSiJxNuDP++WGzV8HU5Bn6faZdXHjSdb4ZWYNybh52dLsNKd5Wu1lArrdGn8u
7wkUDw+IPBOe73wRczqYon12xD+VR2t+3oWN4aJJ79Dd1D+xI1sVKIn0otVbFfFj
B3CVcSoLuv/6F7B0OhksqUdWAAD5AfL1s+wz653stZOKhxMX1S9gbq4A9nQesx45
o2iyjegR7ohJBBgRAgAJBQJO4ix6AhsMAAoJEMrm3ScKl1azQO4An3vR7ZjQ80tD
MkKc5Q91TmwC5A7jAJ9jvRPHOVwYC+sHFL4mOt/9XVaFdg==
=k9wN
-----END PGP PRIVATE KEY BLOCK-----"""
