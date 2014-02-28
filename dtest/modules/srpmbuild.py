#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import subprocess
import unittest

from deploy.errors   import DeployError
from deploy.util     import pps 
from deploy.util     import rxml 

from deploy.modules.core.rpmbuild.gpgsign import InvalidKeyError

from dtest        import (EventTestCase, ModuleTestSuite, _run_make,
                           TestBuild)
from dtest.core   import make_core_suite

from dtest.mixins.rpmbuild import PUBKEY, SECKEY
from dtest.mixins.ddeploy  import prepare_deploy_elem_to_remove_vm

REPODIR  = pps.path(__file__).dirname/'shared' 

class TestSrpmTestCase(EventTestCase):
  """
  The srpmbuild module reads user config and generates classes at runtime. In
  our test case we provide config that causes a class to be generated, and then
  we test the functioning of that class
  """
  moduleid = 'srpmbuild'
  eventid  = 'package1-srpm'
  _type = 'package'

  _run_make(REPODIR)
  _conf = ["""
    <srpmbuild>
    <srpm id='package1'>
      <path>%s/repo1/SRPMS/package1-1.0-1.src.rpm</path>
    </srpm>
    </srpmbuild>
    """ % REPODIR] 

  def __init__(self, os, version, arch, conf=None):
    EventTestCase.__init__(self, os, version, arch, conf=conf)

class Test_ErrorOnDuplicateIds(TestSrpmTestCase):
  "raises an error if multiple srpms provide the same id"
  _conf = """
  <srpmbuild>
  <srpm id="test"/>
  <srpm id="test"/>
  </srpmbuild>
  """

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, DeployError,
      TestBuild, self.conf, options=self.options, args=[])

  def tearDown(self):
    del self.conf


class Test_Config(TestSrpmTestCase):
  "fails if path, repo or script elements not provided"
  _conf = """
    <srpmbuild>
    <srpm id='package1'/>
    </srpmbuild>
    """ 

  def setUp(self): pass

  def runTest(self):
    unittest.TestCase.failUnlessRaises(self, DeployError,
      TestBuild, self.conf, options=self.options, args=[])

  def tearDown(self):
    del self.conf


class Test_FromFolder(TestSrpmTestCase):
  "downloads srpm file from folder"
  _conf = """
    <srpmbuild>
    <srpm id='package1'>
      <path>%s/repo1/SRPMS</path>
    </srpm>
    </srpmbuild>
    """ % REPODIR 

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')


class Test_FromRepo(TestSrpmTestCase):
  "downloads srpm file from repository"
  _conf = """
    <srpmbuild>
    <srpm id='package1'>
      <repo>file://%s/repo1</repo>
    </srpm>
    </srpmbuild>
    """ % REPODIR 

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.failUnless(self.event.io.list_output(what='srpm')[0].basename  == 
                   'package1-1.0-2.src.rpm')


class Test_FromScript(TestSrpmTestCase):
  "uses srpm provided by script"
  _conf = """
      <srpmbuild>
      <srpm id='package1'>
        <script>
        #!/bin/bash
        rm -rf %%{srpm-dir}
        mkdir %%{srpm-dir}
        srpm=%s/repo1/SRPMS/package1-1.0-2.src.rpm
        if [[ $srpm != '%%{srpm-last}' ]]; then 
          cp -a $srpm '%%{srpm-dir}'
        fi
        </script>
      </srpm>
      </srpmbuild>
      """ % REPODIR

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.failUnless(self.event.srpmfile.basename == 'package1-1.0-2.src.rpm')

class Test_UpdatesDefinition(TestSrpmTestCase):
  "updates build machine definition"
  # srpmbuild copies gpgkeys from the parent definition into the srpmbuild
  # machine definition; we test this below
  _conf = [
  """
  <gpgsign>
    <public>%s</public>
    <secret>%s</secret>
  </gpgsign>
  """ % (PUBKEY, SECKEY)]
  _conf.extend(TestSrpmTestCase._conf)

  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_srpm()
    self.event._initialize_builder()
    definition = self.event.builder.definition

    #set some convenience variables
    public = definition.getxpath('/*/gpgsign/public/text()', '')
    secret = definition.getxpath('/*/gpgsign/secret/text()', '')
    parent_repo = self.conf.getxpath('/*/repos/repo[@id="base"]')
    child_repo = definition.getxpath('/*/repos/repo[@id="base"]')

    self.failUnless(len(public) == len(PUBKEY) and
                    len(secret) == len(SECKEY) and
                    child_repo == parent_repo)

class Test_Excludes(TestSrpmTestCase):
  "excludes specified subpackages"
  _conf = """
<srpmbuild>
<srpm id='package1'>
<script>
#!/bin/bash

# create dirs
rm -rf %{srpm-dir}
mkdir -p %{srpm-dir}/SPECS %{srpm-dir}/SRPMS

# create specfile
echo "
%define  _use_internal_dependency_generator 0

Summary: SUMMARY
Name: package1 
Version: 1.0
Release: 1
License: UNKNOWN
Group: Development/Libraries
BuildArch: noarch
%description
DESCRIPTION

%package sub1
Summary: subpackage sub1
Group: Development/Libraries
%description sub1
DESCRIPTION

%package sub2
Summary: subpackage sub2
Group: Development/Libraries
%description sub2
DESCRIPTION

%prep

%build

%install

%clean

%files sub1
%files sub2" > %{srpm-dir}/SPECS/package1.spec 

# build srpm
rpmbuild -bs %{srpm-dir}/SPECS/package1.spec --define "_topdir %{srpm-dir}"

# copy rpm
srpm=%{srpm-dir}/SRPMS/package1-1.0-1.src.rpm
if [[ $srpm != '%{srpm-last}' ]]; then 
  cp -a $srpm '%{srpm-dir}'
fi
</script>
<exclude>package1-sub2</exclude>
</srpm>
</srpmbuild>
"""

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failIf('package1-sub2' in self.event.cvars['rpmbuild-data'])

class Test_InvalidRpm(TestSrpmTestCase):
  "fails on invalid rpms"

  def runTest(self):
    self.event.test_verify_rpms = True
    self.execute_predecessors(self.event)
    self.failUnlessRaises(DeployError, self.event)

class Test_Apply(TestSrpmTestCase):
  "rpmbuild-data added for generated rpm(s)"

  def runTest(self):
    self.tb.dispatch.execute(until=self.event)
    self.failUnless('package1' in self.event.cvars['rpmbuild-data'])

class Test_Shutdown(TestSrpmTestCase):
  "dummy test to delete srpm virtual machine"

  def setUp(self):
    EventTestCase.setUp(self) # do this ahead of pps.path with %{templates_dir}

    # create custom srpmbuild.xml template with remove in post script
    template_file = self.buildroot / 'srpmbuild.xml'
    pps.path('%%{templates-dir}/%s/common/srpmbuild.xml' % self.norm_os).cp(
             template_file.dirname)
    root = rxml.config.parse(template_file, xinclude=True, macros={
                             '%{os}': self.os,
                             '%{version}': self.version,
                             '%{arch}': self.arch,
                             '%{norm-os}': self.norm_os,
                             }).getroot()
    prepare_deploy_elem_to_remove_vm(root.getxpath('/*/publish'))
    root.write(template_file)

    # update config to use custom srpmbuild template
    srpm = self.tb.definition.getxpath('./srpmbuild/srpm')
    rxml.config.Element('template', parent=srpm, text=template_file)

  def runTest(self):
    try:
      self.tb.dispatch.execute(until=self.event)
    except DeployError:
      pass

    self.failIf(subprocess.call('virsh dominfo srpmbuild-%s-%s-%s &> /dev/null'
                                % (self.os, self.version, 
                                   self.arch.replace('_', '-')),
                                shell=True) == 0)

def make_suite(os, version, arch, *args, **kwargs):
  suite = ModuleTestSuite('srpmbuild')

  suite.addTest(make_core_suite(TestSrpmTestCase, os, version, arch, 
                offline=False))

  suite.addTest(Test_ErrorOnDuplicateIds(os, version, arch))
  suite.addTest(Test_Config(os, version, arch))
  suite.addTest(Test_FromFolder(os, version, arch))
  suite.addTest(Test_FromRepo(os, version, arch))
  suite.addTest(Test_FromScript(os, version, arch))

  suite.addTest(Test_UpdatesDefinition(os, version, arch))
  suite.addTest(Test_Excludes(os, version, arch))
  suite.addTest(Test_InvalidRpm(os, version, arch))
  suite.addTest(Test_Apply(os, version, arch))
  suite.addTest(Test_Shutdown(os, version, arch))

  return suite

