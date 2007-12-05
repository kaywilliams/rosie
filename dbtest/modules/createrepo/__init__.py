import unittest

from dims import pps
from dims.xmllib.config import Element

from dimsbuild.modules.core.software.comps import KERNELS

from dbtest      import EventTestCase
from dbtest.core import make_core_suite


class CreaterepoEventTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'createrepo', conf)


class Test_CompsFile(CreaterepoEventTestCase):
  "comps file provided"
  def runTest(self):
    self.tb.dispatch.execute(until='createrepo')
    self.failUnlessExists(self.event.cvars['repodata-directory'] /
                          self.event.cvars['comps-file'].basename)

class Test_SignedRpms(CreaterepoEventTestCase):
  "uses signed rpms when gpgsign is enabled"
  def setUp(self):
    self.options.enabled_modules.append('gpgsign')
    CreaterepoEventTestCase.setUp(self)

    p = Element('gpgsign', parent=self.event.config.get('/distro'))
    # not sure how we want to handle gpg key generation for signing...
    Element('gpg-public-key', parent=p,
            text=p.getroot().file.dirname.abspath()/'RPM-GPG-KEY-test')
    Element('gpg-secret-key', parent=p,
            text=p.getroot().file.dirname.abspath()/'RPM-GPG-SEC-KEY-test')
    Element('gpg-passphrase', parent=p, text='')

  def runTest(self):
    self.tb.dispatch.execute(until='createrepo')
    # no need to test anything specifically; if we get this far we succeeded

  def tearDown(self):
    CreaterepoEventTestCase.tearDown(self)
    self.options.enabled_modules.remove('gpgsign')

def make_suite():
  conf = pps.Path(__file__).dirname/'createrepo.conf'
  suite = unittest.TestSuite()

  suite.addTest(make_core_suite('createrepo', conf))
  suite.addTest(Test_CompsFile(conf))
  suite.addTest(Test_SignedRpms(conf))

  return suite
