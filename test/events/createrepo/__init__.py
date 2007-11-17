import unittest

from dims.xmllib.config import Element

from dimsbuild.modules.core.software.comps import KERNELS

from test      import EventTestCase, EventTestRunner
from test.core import make_core_suite

eventid = 'createrepo'

class CreaterepoEventTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, eventid, conf)

  
class Test_CompsFile(CreaterepoEventTestCase):
  "comps file provided"
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
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
    self.tb.dispatch.execute(until=eventid)
    # no need to test anything specifically; if we get this far we succeeded

def make_suite(conf):
  suite = unittest.TestSuite()
  suite.addTest(make_core_suite(eventid, conf))
  suite.addTest(Test_CompsFile(conf))
  suite.addTest(Test_SignedRpms(conf))
  return suite

def main(suite=None):
  import dims.pps
  config = dims.pps.Path(__file__).dirname/'%s.conf' % eventid
  if suite:
    suite.addTest(make_suite(config))
  else:
    EventTestRunner().run(make_suite(config))


if __name__ == '__main__':
  main()
