from dims import pps

from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_extension_suite
from dbtest.config import make_default_config, add_config_section

class GpgsignTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'gpgsign', conf)

  def runTest(self):
    self.tb.dispatch.execute(until='gpgsign')

def make_suite():
  gpgsignconf = make_default_config('gpgsign')
  add_config_section(gpgsignconf,
    """<gpgsign>
      <gpg-public-key>%s</gpg-public-key>
      <gpg-secret-key>%s</gpg-secret-key>
      <gpg-passphrase></gpg-passphrase>
    </gpgsign>""" % (pps.Path(__file__).abspath().dirname/'RPM-GPG-KEY-test',
                     pps.Path(__file__).abspath().dirname/'RPM-GPG-SEC-KEY-test'))

  suite = ModuleTestSuite('gpgsign')

  suite.addTest(make_extension_suite('gpgsign', gpgsignconf))

  return suite
