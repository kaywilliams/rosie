from dims import pps
from dims import xmllib

from dimsbuild.modules.core.software.comps import KERNELS

from dbtest      import EventTestCase, ModuleTestSuite
from dbtest.core import make_core_suite

class CompsEventTestCase(EventTestCase):
  def __init__(self):
    EventTestCase.__init__(self, 'comps')
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

  def read_comps(self):
    return xmllib.tree.read(self.event.cvars['comps-file'])

  def check_all(self, comps):
    self.check_core(comps)
    self.check_category(comps)
    self.check_groups(comps)

  def check_core(self, comps):
    groups = comps.xpath('/comps/group/id/text()')
    for grp in self.included_groups:
      self.failUnless(grp in groups)

    packages = comps.xpath('/comps/group[id/text()="core"]/packagelist/packagereq/text()')
    for pkg in self.included_pkgs:
      self.failUnless(pkg in packages)

    kfound = False
    for kernel in KERNELS:
      if kernel in packages:
        kfound = True; break
    self.failUnless(kfound)

  def check_category(self, comps):
    self.failUnlessEqual(sorted(comps.xpath('/comps/category/grouplist/groupid/text()')),
                         sorted(self.included_groups))

  def check_groups(self, comps):
    pkgs = comps.xpath('/comps/group/packagelist/packagreq/text()')
    for pkg in self.excluded_pkgs:
      self.failIf(pkg in pkgs)

class Test_Supplied(CompsEventTestCase):
  "comps supplied"
  _conf = "<comps>comps/comps.xml</comps>" # location needs adjustment when config moves

  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    comps_in  = xmllib.tree.read(pps.Path(__file__).dirname/'comps.xml')
    comps_out = self.read_comps()

    self.failUnlessEqual(comps_in, comps_out)

class Test_IncludePackages(CompsEventTestCase):
  "comps generated, groups included in core, kernel unlisted"
  _conf = \
  """<comps>
    <core>
      <group>core</group>
      <group>base</group>
    </core>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    comps = self.read_comps()

    self.included_groups = ['core']
    self.check_all(comps)

    # still need to check that all base pkgs ended up in core group #!

class Test_IncludeCoreGroups(CompsEventTestCase):
  "comps generated, packages included in core"
  _conf = \
  """<comps>
    <core>
      <group>core</group>
      <package>createrepo</package>
      <package>httpd</package>
    </core>
  </comps>"""

  def setUp(self):
    CompsEventTestCase.setUp(self)
    self.event.cvars['included-packages'] = set(['kde', 'xcalc'])

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core']
    self.included_pkgs = ['createrepo', 'httpd', 'kde', 'xcalc']
    self.check_all(self.read_comps())

class Test_IncludeGroups(CompsEventTestCase):
  "comps generated, groups included"
  _conf = \
  """<comps>
    <groups>
      <group>base</group>
      <group>printing</group>
    </groups>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

class Test_ExcludePackages(CompsEventTestCase):
  "comps generated, packages excluded"
  _conf = \
  """<comps>
    <exclude>
      <package>cpio</package>
      <package>kudzu</package>
    </exclude>
  </comps>"""

  def setUp(self):
    CompsEventTestCase.setUp(self)
    self.event.cvars['excluded-packages'] = set(['passwd', 'setup'])

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core']
    self.excluded_pkgs = ['cpio', 'kudzu', 'passwd', 'setup']
    self.check_all(self.read_comps())

class Test_GroupsByRepo(CompsEventTestCase):
  "comps generated, group included from specific repo"
  _conf = \
  """<comps>
    <core>
      <group repoid="fedora-6-base">core</group>
    </core>
    <groups>
      <group>base</group>
      <group repoid="fedora-6-base">printing</group>
    </groups>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

    # still need to check 'core' and 'printing' came from 'fedora-6-base' #!

class Test_MultipleGroupfiles(CompsEventTestCase):
  "comps generated, multiple repositories with groupfiles"
  _conf = \
  """<comps>
    <core>
      <group repooid="fedora-6-base">core</groups>
    </core>
    <groups>
      <group>base-x</group>
    </groups>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base-x']
    self.check_all(self.read_comps())

    # still need to check that 'base-x' contains all packages listed in #!
    # both 'fedora-6-base' and 'livna' groupfiles in 'base-x' group #!

class Test_GroupDefaults(CompsEventTestCase):
  # bug 106
  "comps generated, group defaults set appropriately"
  _conf = \
  """<comps>
    <groups>
      <group>base</group>
      <group default="true">web-server</group>
      <group default="false">printing</group>
    </groups>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    comps = self.read_comps()

    for group in ['web-server', 'printing']:
      self.failUnlessEqual(
        comps.get('/comps/group[id/text()="%s"]/default/text()' % group),
        self.event.config.get('groups/group[text()="%s"]/@default' % group))

    # still need to test 'default' for both 'true' and 'false' #!

def make_suite():
  suite = ModuleTestSuite('comps')

  suite.addTest(make_core_suite('comps'))
  suite.addTest(Test_Supplied())
  suite.addTest(Test_IncludePackages())
  suite.addTest(Test_IncludeCoreGroups())
  suite.addTest(Test_IncludeGroups())
  suite.addTest(Test_ExcludePackages())
  suite.addTest(Test_GroupsByRepo())
  ##suite.addTest(Test_MultipleGroupfiles())
  suite.addTest(Test_GroupDefaults())

  return suite
