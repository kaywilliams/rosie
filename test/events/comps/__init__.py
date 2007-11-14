import unittest

from dims import xmllib

from dimsbuild.modules.core.software.comps import KERNELS

from test import EventTest

from test.events.core import make_suite as core_make_suite

eventid = 'comps'

class CompsEventTest(EventTest):
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)
    self.included_groups = []
    self.included_pkgs = []
    self.excluded_pkgs = []
  
  def setUp(self):
    EventTest.setUp(self)
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
  
class Test_Supplied(CompsEventTest):
  "comps supplied"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.supplied')
    self.confdir = confdir
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    comps_in  = xmllib.tree.read(self.confdir/'comps.xml')
    comps_out = self.read_comps()
    
    self.failUnlessEqual(comps_in, comps_out)

class Test_IncludePackages(CompsEventTest):
  "comps generated, groups included in core, kernel unlisted"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.include-packages')
    self.included_groups = ['core']
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    comps = self.read_comps()
    
    self.check_all(comps)
    
    # still need to check that all base pkgs ended up in core group #!

class Test_IncludeCoreGroups(CompsEventTest):
  "comps generated, packages included in core"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.include-core-groups')
    self.included_groups = ['core']
    self.included_pkgs = ['createrepo', 'httpd', 'kde', 'xcalc']
  
  def setUp(self):
    CompsEventTest.setUp(self)
    self.event.cvars['included-packages'] = ['kde', 'xcalc']
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_all(self.read_comps())

class Test_IncludeGroups(CompsEventTest):
  "comps generated, groups included"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.include-groups')
    self.included_groups = ['core', 'base', 'printing']
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_all(self.read_comps())

class Test_ExcludePackages(CompsEventTest):
  "comps generated, packages excluded"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.exclude-packages')
    self.included_groups = ['core']
    self.excluded_pkgs = ['cpio', 'kudzu', 'passwd', 'setup']
  
  def setUp(self):
    CompsEventTest.setUp(self)
    self.event.cvars['excluded-packages'] = ['passwd', 'setup']
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_all(self.read_comps())

class Test_GroupsByRepo(CompsEventTest):
  "comps generated, group included from specific repo"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.groups-by-repo')
    self.included_groups = ['core', 'base', 'printing']
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_all(self.read_comps())
    
    # still need to check 'core' and 'printing' came from 'fedora-6-base' #!

class Test_MultipleGroupfiles(CompsEventTest):
  "comps generated, multiple repositories with groupfiles"
  def __init__(self, confdir):
    CompsEventTest.__init__(self, eventid, confdir/'conf.multiple-groupfiles')
    self.included_groups = ['core', 'base-x']
  
  def runTest(self):
    self.tb.dispatch.execute(until=eventid)
    
    self.check_all(self.read_comps())
    
    # still need to check that 'base-x' contains all packages listed in #!
    # both 'fedora-6-base' and 'livna' groupfiles in 'base-x' group #!

def make_suite(confdir):
  suite = unittest.TestSuite()
  suite.addTest(core_make_suite(eventid, confdir/'conf.supplied'))
  suite.addTest(Test_Supplied(confdir))
  suite.addTest(Test_IncludePackages(confdir))
  suite.addTest(Test_IncludeCoreGroups(confdir))
  suite.addTest(Test_IncludeGroups(confdir))
  suite.addTest(Test_ExcludePackages(confdir))
  suite.addTest(Test_GroupsByRepo(confdir))
  suite.addTest(Test_MultipleGroupfiles(confdir))
  return suite

def main():
  import dims.pps
  runner = unittest.TextTestRunner(verbosity=2)
  
  suite = make_suite(dims.pps.Path(__file__).dirname)
  
  runner.stream.writeln("testing event '%s'" % eventid)
  runner.run(suite)


if __name__ == '__main__':
  main()
