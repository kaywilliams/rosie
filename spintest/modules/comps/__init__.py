from rendition import pps
from rendition import xmllib

from spin.modules.core.software.comps import KERNELS

from spintest      import EventTestCase, ModuleTestSuite
from spintest.core import make_core_suite

class CompsEventTestCase(EventTestCase):
  moduleid = 'comps'
  eventid  = 'comps'

class _CompsEventTestCase(CompsEventTestCase):
  def __init__(self, basedistro, arch, conf=None):
    CompsEventTestCase.__init__(self, basedistro, arch, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []

  def setUp(self):
    CompsEventTestCase.setUp(self)
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

class Test_Supplied(_CompsEventTestCase):
  "comps supplied"
  _conf = "<comps>comps/comps.xml</comps>" # location needs adjustment when config moves

  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    comps_in  = xmllib.tree.read(pps.Path(__file__).dirname/'comps.xml')
    comps_out = self.read_comps()

    self.failUnlessEqual(comps_in, comps_out)

class Test_IncludePackages(_CompsEventTestCase):
  "comps generated, groups included in core, kernel unlisted"
  _conf = \
  """<comps>
    <group>core</group>
    <group>base</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    comps = self.read_comps()

    self.included_groups = ['core', 'base']
    self.check_all(comps)

class Test_IncludeCoreGroups(_CompsEventTestCase):
  "comps generated, packages included in core"
  _conf = \
  """<comps>
    <group>core</group>
    <package>createrepo</package>
    <package>httpd</package>
  </comps>"""

  def setUp(self):
    _CompsEventTestCase.setUp(self)
    self.event.cvars['comps-included-packages'] = set(['kde', 'xcalc'])

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core']
    self.included_pkgs = ['createrepo', 'httpd', 'kde', 'xcalc']
    self.check_all(self.read_comps())

class Test_IncludeGroups(_CompsEventTestCase):
  "comps generated, groups included"
  _conf = \
  """<comps>
    <group>base</group>
    <group>printing</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

class Test_ExcludePackages(_CompsEventTestCase):
  "comps generated, packages excluded"
  _conf = \
  """<comps>
    <exclude-package>cpio</exclude-package>
    <exclude-package>kudzu</exclude-package>
  </comps>"""

  def setUp(self):
    _CompsEventTestCase.setUp(self)
    self.event.cvars['comps-excluded-packages'] = set(['passwd', 'setup'])

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core']
    self.excluded_pkgs = ['cpio', 'kudzu', 'passwd', 'setup']
    self.check_all(self.read_comps())

class Test_GroupsByRepo(_CompsEventTestCase):
  "comps generated, group included from specific repo"
  _conf = \
  """<comps>
    <group repoid="%(basedistro)s-base">core</group>
    <group>base</group>
    <group repoid="%(basedistro)s-base">printing</group>
  </comps>"""
  def __init__(self, basedistro, arch, conf=None):
    self._conf = self._conf % {'basedistro': basedistro}
    _CompsEventTestCase.__init__(self, basedistro, arch, conf)

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

    # still need to check 'core' and 'printing' came from '$basedistro-base' #!

class Test_MultipleGroupfiles(_CompsEventTestCase):
  "comps generated, multiple repositories with groupfiles"
  _conf = \
  """<comps>
    <group repooid="%(basedistro)s-base">core</groups>
    <group>base-x</group>
  </comps>"""
  def __init__(self, basedistro, arch, conf=None):
    self._conf = self._conf % {'basedistro': basedistro}
    _CompsEventTestCase.__init__(self, basedistro, arch, conf)

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    self.included_groups = ['core', 'base-x']
    self.check_all(self.read_comps())

    # still need to check that 'base-x' contains all packages listed in #!
    # both '$basedistro-base' and 'livna' groupfiles in 'base-x' group #!

class Test_GroupDefaults(_CompsEventTestCase):
  # bug 106
  "comps generated, group defaults set appropriately"
  _conf = \
  """<comps>
    <group>base</group>
    <group default="true">web-server</group>
    <group default="false">printing</group>
  </comps>"""

  def runTest(self):
    self.tb.dispatch.execute(until='comps')

    comps = self.read_comps()

    for group in ['web-server', 'printing']:
      self.failUnlessEqual(
        comps.get('/comps/group[id/text()="%s"]/default/text()' % group),
        self.event.config.get('group[text()="%s"]/@default' % group))

    # still need to test 'default' for both 'true' and 'false' #!

def make_suite(basedistro, arch):
  suite = ModuleTestSuite('comps')

  suite.addTest(make_core_suite(CompsEventTestCase, basedistro, arch))
  suite.addTest(Test_Supplied(basedistro, arch))
  suite.addTest(Test_IncludePackages(basedistro, arch))
  suite.addTest(Test_IncludeCoreGroups(basedistro, arch))
  suite.addTest(Test_IncludeGroups(basedistro, arch))
  suite.addTest(Test_ExcludePackages(basedistro, arch))
  suite.addTest(Test_GroupsByRepo(basedistro, arch))
  ##suite.addTest(Test_MultipleGroupfiles(basedistro, arch))
  suite.addTest(Test_GroupDefaults(basedistro, arch))

  return suite
