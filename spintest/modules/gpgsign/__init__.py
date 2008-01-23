from dims import pps

from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_extension_suite

class GpgsignTestCase(EventTestCase):
  moduleid = 'gpgsign'
  eventid  = 'gpgsign'
  _conf = """<gpgsign>
    <public-key>%s</public-key>
    <secret-key>%s</secret-key>
    <passphrase></passphrase>
  </gpgsign>""" % (pps.Path(__file__).abspath().dirname/'RPM-GPG-KEY-test',
                   pps.Path(__file__).abspath().dirname/'RPM-GPG-SEC-KEY-test')

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('gpgsign')

  suite.addTest(make_extension_suite(GpgsignTestCase, basedistro, arch))

  return suite
