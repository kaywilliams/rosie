import unittest

from dims import pps
from dims import xmllib

from dimsbuild.modules.core.software.comps import KERNELS

from test      import EventTestCase
from test.core import make_core_suite

class CompsEventTestCase(EventTestCase):
  def __init__(self, conf):
    EventTestCase.__init__(self, 'comps', conf)
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
  def __init__(self, conf):
    CompsEventTestCase.__init__(self, conf)
  
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    comps_in  = xmllib.tree.read(self.conf.dirname/'comps.xml')
    comps_out = self.read_comps()
    
    self.failUnlessEqual(comps_in, comps_out)

class Test_IncludePackages(CompsEventTestCase):
  "comps generated, groups included in core, kernel unlisted"
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    
    comps = self.read_comps()
    
    self.included_groups = ['core']
    self.check_all(comps)
    
    # still need to check that all base pkgs ended up in core group #!

class Test_IncludeCoreGroups(CompsEventTestCase):
  "comps generated, packages included in core"
  def setUp(self):
    CompsEventTestCase.setUp(self)
    self.event.cvars['included-packages'] = ['kde', 'xcalc']
  
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    
    self.included_groups = ['core']
    self.included_pkgs = ['createrepo', 'httpd', 'kde', 'xcalc']
    self.check_all(self.read_comps())

class Test_IncludeGroups(CompsEventTestCase):
  "comps generated, groups included"
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    
    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())

class Test_ExcludePackages(CompsEventTestCase):
  "comps generated, packages excluded"
  def setUp(self):
    CompsEventTestCase.setUp(self)
    self.event.cvars['excluded-packages'] = ['passwd', 'setup']
  
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    
    self.included_groups = ['core']
    self.excluded_pkgs = ['cpio', 'kudzu', 'passwd', 'setup']
    self.check_all(self.read_comps())

class Test_GroupsByRepo(CompsEventTestCase):
  "comps generated, group included from specific repo"
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    
    self.included_groups = ['core', 'base', 'printing']
    self.check_all(self.read_comps())
    
    # still need to check 'core' and 'printing' came from 'fedora-6-base' #!

class Test_MultipleGroupfiles(CompsEventTestCase):
  "comps generated, multiple repositories with groupfiles"
  def runTest(self):
    self.tb.dispatch.execute(until='comps')
    
    self.included_groups = ['core', 'base-x']
    self.check_all(self.read_comps())
    
    # still need to check that 'base-x' contains all packages listed in #!
    # both 'fedora-6-base' and 'livna' groupfiles in 'base-x' group #!

def make_suite():
  confdir = pps.Path(__file__).dirname
  suite = unittest.TestSuite()
  
  suite.addTest(make_core_suite('comps', confdir/'conf.supplied'))
  suite.addTest(Test_Supplied(confdir/'conf.supplied'))
  suite.addTest(Test_IncludePackages(confdir/'conf.include-packages'))
  suite.addTest(Test_IncludeCoreGroups(confdir/'conf.include-core-groups'))
  suite.addTest(Test_IncludeGroups(confdir/'conf.include-groups'))
  suite.addTest(Test_ExcludePackages(confdir/'conf.exclude-packages'))
  suite.addTest(Test_GroupsByRepo(confdir/'conf.groups-by-repo'))
  suite.addTest(Test_MultipleGroupfiles(confdir/'conf.multiple-groupfiles'))
  
  return suite
