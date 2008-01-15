from StringIO import StringIO

import unittest

from rendition import pps
from rendition import xmllib

from spintest      import EventTestCase, ModuleTestSuite, config, _run_make
from spintest.core import make_core_suite

class DownloadEventTestCase(EventTestCase):
  moduleid = 'download'
  eventid  = 'download'

  def __init__(self, basedistro, conf=None):
    EventTestCase.__init__(self, basedistro, conf=conf)

    config.add_config_section(self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro),
         config._make_repo('%s-updates' % basedistro),
         xmllib.config.read(StringIO('<repofile>download/download-test-repos.repo</repofile>'))]
      )
    )

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
  "Test that the packages in <comps> are downloaded."
  _conf = """
  <comps>
    <core>
      <package>package1</package>
      <package>package2</package>
    </core>
  </comps>
  """

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
  "Test that the previously-downloaded packages are removed"
  def runTest(self):
    # add a package, then remove it
    self.tb.dispatch.execute(until='download')
    for package in self.event.io.list_output():
      pkgname = self.event._deformat(package)[1]
      self.failIf(pkgname == 'package1' or pkgname == 'package2')

class Test_ArchChanges(DownloadEventTestCase):
  "Test arch changes in <main/>"
  def __init__(self, basedistro):
    DownloadEventTestCase.__init__(self, basedistro)
    xmllib.tree.uElement('arch', self.conf.get('/distro/main'), text='i386')

class Test_MultipleReposWithSamePackage(DownloadEventTestCase):
  "Test multiple repos with the same package."
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
  _run_make(pps.Path(__file__).dirname)
  suite = ModuleTestSuite('download')
  suite.addTest(make_core_suite(DownloadEventTestCase, basedistro))
  suite.addTest(Test_PackagesDownloaded(basedistro))
  suite.addTest(Test_AddedPackageDownloaded(basedistro))
  suite.addTest(Test_RemovedPackageDeleted(basedistro))
  suite.addTest(Test_ArchChanges(basedistro))
  suite.addTest(Test_MultipleReposWithSamePackage(basedistro))
  return suite
