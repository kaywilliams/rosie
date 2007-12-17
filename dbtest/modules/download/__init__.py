import unittest

from dims import pps
from dims import xmllib

from dbtest      import EventTestCase
from dbtest.core import make_core_suite

class DownloadEventTestCase(EventTestCase):
  moduleid = 'download'
  eventid  = 'download'

  def __init__(self, basedistro, conf=None):
    EventTestCase.__init__(self, basedistro, conf)

  def runTest(self):
    self.tb.dispatch.execute(until='download')
    for rpm in self.event.io.list_output():
      self.failUnlessExists(rpm)
      _,_,_,_,a = self.event._deformat(rpm)
      self.failUnless(a in self.event._validarchs)

class Test_PackagesDownloaded(DownloadEventTestCase):
  "Test to see that all packages are downloaded."
  pass

class Test_AddedPackageDownloaded(DownloadEventTestCase):
  "Test that the 'httpd' package is downloaded."
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
  def setUp(self):
    DownloadEventTestCase.setUp(self)

  def runTest(self):
    # add a package, then remove it
    self.tb.dispatch.execute(until='download')
    for package in self.event.io.list_output():
      pkgname = self.event._deformat(package)[1]
      self.failIf(pkgname == 'package1' or pkgname == 'package2')

class Test_ArchChanges(DownloadEventTestCase):
  def setUp(self):
    DownloadEventTestCase.setUp(self)
    xmllib.tree.Element('arch', self.event._config.get('/distro/main'), text='i386')

class Test_MultipleReposWithSamePackage(DownloadEventTestCase):
  def runTest(self):
    DownloadEventTestCase.runTest(self)
    # if the length of cvars['cached-rpms'] is equal to the length of
    # packages in cvars['rpms-by-repoid'], then we know for sure that
    # we are downloading a package from exactly one repository.
    numpkgs = 0
    for id in self.event.cvars['rpms-by-repoid']:
      numpkgs += len(self.event.cvars['rpms-by-repoid'][id])
    self.failUnless(len(self.event.cvars['cached-rpms']) == numpkgs)

def make_suite(basedistro):
  conf = pps.Path(__file__).dirname/'f8.conf'
  suite = unittest.TestSuite()
  return suite #!

  suite.addTest(make_core_suite('download', conf))
  suite.addTest(Test_PackagesDownloaded(conf))
  suite.addTest(Test_AddedPackageDownloaded(conf))
  suite.addTest(Test_RemovedPackageDeleted(conf))
  suite.addTest(Test_ArchChanges(conf))
  suite.addTest(Test_MultipleReposWithSamePackage(conf))

  return suite
