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
      _,_,_,_,a = self.event._deformat(rpm)
      self.failUnless(a in self.event._validarchs)

class Test_PackagesDownloaded(DownloadEventTestCase):
  "Test to see that all packages are downloaded."
  pass

class Test_AddedPackageDownloaded(DownloadEventTestCase):
  "Test that the 'httpd' package is downloaded."
  def __init__(self, conf):
    DownloadEventTestCase.__init__(self, conf)

  def setUp(self):
    DownloadEventTestCase.setUp(self)
    comps = xmllib.tree.Element('comps', self.event._config)
    core = xmllib.tree.Element('core', comps)
    pkg1 = xmllib.tree.Element('package', core, text='package1')
    pkg2 = xmllib.tree.Element('package', core, text='package2')

  def runTest(self):
    DownloadEventTestCase.runTest(self)
    found1 = False
    found2 = False
    for package in self.event.io.list_output():
      if self.event._deformat(package)[1] == 'package1':
        found1 = True
      if self.event._deformat(package)[1] == 'package2':
        found2 = True
    self.failUnless(found1 and found2)

class Test_RemovedPackageDeleted(DownloadEventTestCase):
  "Test that the previously-added 'httpd' package is removed"
  def __init__(self, conf):
    DownloadEventTestCase.__init__(self, conf)

  def setUp(self):
    DownloadEventTestCase.setUp(self)

  def runTest(self):
    # add a package, then remove it
    self.tb.dispatch.execute(until=eventid)
    for package in self.event.io.list_output():
      pkgname = self.event._deformat(package)[1]
      self.failIf(pkgname == 'package1' or pkgname == 'package2')

class Test_ArchChanges(DownloadEventTestCase):
  def __init__(self, conf):
    DownloadEventTestCase.__init__(self, conf)

  def setUp(self):
    DownloadEventTestCase.setUp(self)
    xmllib.tree.Element('arch', self.event._config.get('/distro/main'), text='i386')

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_PackagesDownloaded(conf))
  suite.addTest(Test_AddedPackageDownloaded(conf))
  suite.addTest(Test_RemovedPackageDeleted(conf))
  suite.addTest(Test_ArchChanges(conf))
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
