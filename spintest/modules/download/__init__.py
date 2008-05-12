#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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
from StringIO import StringIO

import unittest

from rendition import pps
from rendition import xmllib

from spintest      import EventTestCase, ModuleTestSuite, config, _run_make
from spintest.core import make_core_suite

class DownloadEventTestCase(EventTestCase):
  moduleid = 'download'
  eventid  = 'download'

  def __init__(self, basedistro, arch, conf=None):
    EventTestCase.__init__(self, basedistro, arch, conf=conf)

    config.add_config_section(self.conf,
      config.make_repos(basedistro,
        [config._make_repo('%s-base' % basedistro, arch),
         config._make_repo('%s-updates' % basedistro, arch),
         xmllib.config.read(StringIO('<repofile>download/download-test-repos.repo</repofile>'))]
      )
    )

  def runTest(self):
    self.tb.dispatch.execute(until='download')
    for rpm in self.event.io.list_output():
      self.failUnlessExists(rpm)
      _,_,_,_,a = self.event._deformat(rpm)
      self.failUnless(a in self.event._validarchs)

class Test_PackagesDownloaded(DownloadEventTestCase):
  "Test to see that all packages are downloaded."
  pass

class Test_AddedPackageDownloaded(DownloadEventTestCase):
  "Test that the packages in <comps> are downloaded."
  _conf = """<comps>
    <package>package1</package>
    <package>package2</package>
  </comps>"""

  def runTest(self):
    DownloadEventTestCase.runTest(self)
    found1 = False
    found2 = False
    for package in self.event.io.list_output():
      if self.event._deformat(package)[1] == 'package1':
        found1 = True
      if self.event._deformat(package)[1] == 'package2':
        found2 = True
    self.failUnless(found1 and found2)

class Test_RemovedPackageDeleted(DownloadEventTestCase):
  "Test that the previously-downloaded packages are removed"
  def runTest(self):
    # add a package, then remove it
    self.tb.dispatch.execute(until='download')
    for package in self.event.io.list_output():
      pkgname = self.event._deformat(package)[1]
      self.failIf(pkgname == 'package1' or pkgname == 'package2')

class Test_ArchChanges(DownloadEventTestCase):
  "Test arch changes in <main/>"
  def __init__(self, basedistro, arch):
    DownloadEventTestCase.__init__(self, basedistro, arch)
    xmllib.tree.uElement('arch', self.conf.get('/distro/main'), text='i386')

class Test_MultipleReposWithSamePackage(DownloadEventTestCase):
  "Test multiple repos with the same package."
  def runTest(self):
    DownloadEventTestCase.runTest(self)
    # if the length of cvars['cached-rpms'] is equal to the length of
    # packages in cvars['rpms-by-repoid'], then we know for sure that
    # we are downloading a package from exactly one repository.
    numpkgs = 0
    for id in self.event.cvars['rpms-by-repoid']:
      numpkgs += len(self.event.cvars['rpms-by-repoid'][id])
    self.failUnless(len(self.event.cvars['cached-rpms']) == numpkgs)

def make_suite(basedistro, arch):
  _run_make(pps.path(__file__).dirname)

  suite = ModuleTestSuite('download')

  suite.addTest(make_core_suite(DownloadEventTestCase, basedistro, arch))
  suite.addTest(Test_PackagesDownloaded(basedistro, arch))
  suite.addTest(Test_AddedPackageDownloaded(basedistro, arch))
  suite.addTest(Test_RemovedPackageDeleted(basedistro, arch))
  suite.addTest(Test_ArchChanges(basedistro, arch))
  suite.addTest(Test_MultipleReposWithSamePackage(basedistro, arch))

  return suite
