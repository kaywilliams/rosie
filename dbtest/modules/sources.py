from dbtest        import EventTestCase, ModuleTestSuite
from dbtest.core   import make_extension_suite

CONF = """<sources>
  <repo id='fedora-6-base-source'>
    <name>fedora-6-base-source</name>
    <baseurl>http://www.abodiosoftware.com/open_software/fedora/core/6/source/SRPMS/</baseurl>
  </repo>
</sources>"""

class SourceReposEventTestCase(EventTestCase):
  moduleid = 'sources'
  eventid  = 'source-repos'
  _conf = CONF

class SourcesEventTestCase(EventTestCase):
  moduleid = 'sources'
  eventid  = 'sources'
  _conf = CONF

def make_suite():
  suite = ModuleTestSuite('sources')

  suite.addTest(make_extension_suite(SourceReposEventTestCase))
  suite.addTest(make_extension_suite(SourcesEventTestCase))

  return suite
