from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_extension_suite
from dbtest.config import make_default_config, add_config_section

class SourcesTestCase(EventTestCase):
  def __init__(self, conf=None):
    EventTestCase.__init__(self, 'sources', conf)

def make_suite():
  sourcesconf = make_default_config('sources')
  add_config_section(sourcesconf,
  '''<sources>
    <repo id='fedora-6-base-source'>
      <name>fedora-6-base-source</name>
      <baseurl>http://www.abodiosoftware.com/open_software/fedora/core/6/source/SRPMS/</baseurl>
    </repo>
  </sources>''')
  suite = ModuleTestSuite('sources')

  suite.addTest(make_extension_suite('source-repos', sourcesconf))
  suite.addTest(make_extension_suite('sources', sourcesconf))

  return suite
