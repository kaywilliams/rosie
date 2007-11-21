import unittest

from dims import xmllib

from test import EventTestCase, EventTestRunner
from test.core import make_core_suite

eventid = 'download'

class DownloadEventTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, eventid, conf)

  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    for rpm in self.event.io.list_output():
      self.failUnlessExists(rpm)

class Test_PackagesDownloaded(DownloadEventTestCase):
  pass

class Test_AddedPackageDownloaded(DownloadEventTestCase):
  def __init__(self, conf):
    DownloadEventTestCase.__init__(self, conf)

  def setUp(self):
    DownloadEventTestCase.setUp(self)
    comps = xmllib.tree.Element('comps', self.event._config)
    core  = xmllib.tree.Element('core', comps)
    httpd = xmllib.tree.Element('package', core, text='httpd')

  def runTest(self):
    DownloadEventTestCase.runTest(self)
    found = False
    for package in self.event.io.list_output():
      if self.event._deformat(package)[1] == 'httpd':
        found = True
        break
    self.failUnless(found)

class Test_RemovedPackageDeleted(DownloadEventTestCase):
  def __init__(self, conf):
    DownloadEventTestCase.__init__(self, conf)

  def setUp(self):
    DownloadEventTestCase.setUp(self)

  def runTest(self):
    # add a package, then remove it
    self.tb.dispatch.execute(until=eventid)
    for package in self.event.io.list_output():
      self.failIf(self.event._deformat(package)[1] == 'httpd')

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_PackagesDownloaded(conf))
  suite.addTest(Test_AddedPackageDownloaded(conf))
  suite.addTest(Test_RemovedPackageDeleted(conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'f8.conf'
  if suite:
    suite.addTest(make_suite(config))
  else:
    EventTestRunner().run(make_suite(config))

if __name__ == '__main__':
  main()

