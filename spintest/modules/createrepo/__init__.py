from dims import pps
from dims.xmllib.config import Element

from dimsbuild.modules.core.software.comps import KERNELS

from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite


class CreaterepoEventTestCase(EventTestCase):
  moduleid = 'createrepo'
  eventid  = 'createrepo'


class Test_CompsFile(CreaterepoEventTestCase):
  "comps file provided"
  def runTest(self):
    self.tb.dispatch.execute(until='createrepo')
    self.failUnlessExists(self.event.cvars['repodata-directory'] /
                          self.event.cvars['comps-file'].basename)

class Test_SignedRpms(CreaterepoEventTestCase):
  "uses signed rpms when gpgsign is enabled"
  _conf = """<gpgsign>
    <public-key>%s</public-key>
    <secret-key>%s</secret-key>
    <passphrase></passphrase>
  </gpgsign>""" % (pps.Path(__file__).dirname.abspath()/'RPM-GPG-KEY-test',
                   pps.Path(__file__).dirname.abspath()/'RPM-GPG-SEC-KEY-test')

  def runTest(self):
    self.tb.dispatch.execute(until='createrepo')
    # no need to test anything specifically; if we get this far we succeeded

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('createrepo')

  suite.addTest(make_core_suite(CreaterepoEventTestCase, basedistro, arch))
  suite.addTest(Test_CompsFile(basedistro, arch))
  suite.addTest(Test_SignedRpms(basedistro, arch))

  return suite
