import unittest

from dims import pps
from dims import xmllib

from dbtest      import EventTestCase
from dbtest.core import make_core_suite

class ReleaseFilesEventTestCase(EventTestCase):
  def __init__(self, conf, enabled='True'):
    EventTestCase.__init__(self, 'release-files', conf)
    self.enabled = enabled

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()
    xmllib.tree.Element('release-rpm', self.event._config, attrs={'enabled': self.enabled})

  def runTest(self):
    self.tb.dispatch.execute(until='publish')

class Test_ReleaseFiles(ReleaseFilesEventTestCase):
  pass

class Test_ReleaseFilesWithDefaultSet(ReleaseFilesEventTestCase):
  def setUp(self):
    ReleaseFilesEventTestCase.setUp(self)
    rfiles = xmllib.tree.Element('release-files', self.event._config)
    xmllib.tree.Element('include-in-tree', rfiles, attrs={'use-default-set': 'True'})

class Test_ReleaseFilesWithDefaultSet(ReleaseFilesEventTestCase):
  def setUp(self):
    ReleaseFilesEventTestCase.setUp(self)
    rfiles = xmllib.tree.Element('release-files', self.event._config)
    xmllib.tree.Element('include-in-tree', rfiles, attrs={'use-default-set': 'False'})

class Test_ReleaseFilesWithInputFiles(ReleaseFilesEventTestCase):
  def setUp(self):
    ReleaseFilesEventTestCase.setUp(self)
    rfiles = xmllib.tree.Element('release-files', self.event._config)
    xmllib.tree.Element('path', rfiles, text='input1')
    xmllib.tree.Element('path', rfiles, text='input2', attrs={'dest': 'dir1/dir2'})
    xmllib.tree.Element('path', rfiles, text='input3', attrs={'dest':'dir3'})

  def runTest(self):
    ReleaseFilesEventTestCase.runTest(self)
    for file in [ self.event.SOFTWARE_STORE / 'input1',
                  self.event.SOFTWARE_STORE / 'dir1/dir2/input2',
                  self.event.SOFTWARE_STORE / 'dir3/input3']:
      self.failUnless(file.exists())

class Test_ReleaseFilesWithPackageElement(ReleaseFilesEventTestCase):
  def __init__(self, conf):
    ReleaseFilesEventTestCase.__init__(self, conf, 'True')

  def setUp(self):
    ReleaseFilesEventTestCase.setUp(self)
    rfiles = xmllib.tree.Element('release-files', self.event._config)
    xmllib.tree.Element('package', rfiles, text='%s-release' % self.event.product)

def make_suite():
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('release-files', confdir/'fedora6.conf'))
  for config in [ confdir / 'fedora6.conf',
                  confdir / 'fedora7.conf',
                  confdir / 'fedora8.conf',
                  confdir / 'centos5.conf',
                  confdir / 'redhat5.conf']:
    # default run
    suite.addTest(Test_ReleaseFiles(config, 'True'))
    suite.addTest(Test_ReleaseFiles(config, 'False'))

    # execution with modification of 'use-default-set' attribute
    suite.addTest(Test_ReleaseFilesWithDefaultSet(config, 'True'))
    suite.addTest(Test_ReleaseFilesWithDefaultSet(config, 'False'))

    # execution with <path/> element
    suite.addTest(Test_ReleaseFilesWithInputFiles(config, 'True'))
    suite.addTest(Test_ReleaseFilesWithInputFiles(config, 'False'))

    # execution with <package/> element
    suite.addTest(Test_ReleaseFilesWithPackageElement(config))
  return suite
