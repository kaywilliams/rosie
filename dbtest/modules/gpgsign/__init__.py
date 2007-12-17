from dims import pps

from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_extension_suite

class GpgsignTestCase(EventTestCase):
  moduleid = 'gpgsign'
  eventid  = 'gpgsign'
  _conf = """<gpgsign>
    <gpg-public-key>%s</gpg-public-key>
    <gpg-secret-key>%s</gpg-secret-key>
    <gpg-passphrase></gpg-passphrase>
  </gpgsign>""" % (pps.Path(__file__).abspath().dirname/'RPM-GPG-KEY-test',
                   pps.Path(__file__).abspath().dirname/'RPM-GPG-SEC-KEY-test')

def make_suite(basedistro):
  suite = ModuleTestSuite('gpgsign')

  suite.addTest(make_extension_suite(GpgsignTestCase, basedistro))

  return suite
