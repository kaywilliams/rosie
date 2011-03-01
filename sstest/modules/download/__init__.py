#
# Copyright (c) 2011
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

from systemstudio.util import pps
from systemstudio.util import rxml
from systemstudio.util.repo import RPM_PNVRA_REGEX

from sstest      import EventTestCase, ModuleTestSuite, _run_make
from sstest.core import make_core_suite

class DownloadEventTestCase(EventTestCase):
  moduleid = 'download'
  eventid  = 'download'

  def _make_repos_config(self):
    repos = EventTestCase._make_repos_config(self)

    rxml.config.Element('repofile', text='download/download-test-repos.repo', parent=repos)

    return repos

  def _deformat(self, rpm):
    """
    p[ath],n[ame],v[ersion],r[elease],a[rch] = _deformat(rpm)

    Takes an rpm with an optional path prefix and splits it into its component parts.
    Returns a path, name, version, release, arch tuple.
    """
    try:
      return RPM_PNVRA_REGEX.match(rpm).groups()
    except (AttributeError, IndexError), e:
      self.log(2, L2("DEBUG: Unable to extract rpm information from name '%s'" % rpm))
      return (None, None, None, None, None)

  def runTest(self):
    self.tb.dispatch.execute(until='download')
    for rpm in self.event.io.list_output():
      self.failUnlessExists(rpm)
      _,_,_,_,a = self._deformat(rpm)
      self.failUnless(a in self.event._validarchs)

class Test_PackagesDownloaded(DownloadEventTestCase):
  "Test to see that all packages are downloaded"
  pass

class Test_AddedPackageDownloaded(DownloadEventTestCase):
  "Test that the packages in <packages> are downloaded"
  _conf = """<packages>
    <package>package1</package>
    <package>package2</package>
  </packages>"""

  def runTest(self):
    DownloadEventTestCase.runTest(self)
    found1 = False
    found2 = False
    for package in self.event.io.list_output():
      if self._deformat(package)[1] == 'package1':
        found1 = True
      if self._deformat(package)[1] == 'package2':
        found2 = True
    self.failUnless(found1 and found2)

class Test_RemovedPackageDeleted(DownloadEventTestCase):
  "Test that the previously-downloaded packages are removed"
  def runTest(self):
    # added a package in previous test case, which should now be
    # removed
    DownloadEventTestCase.runTest(self)
    for package in self.event.io.list_output():
      pkgname = self._deformat(package)[1]
      self.failIf(pkgname == 'package1' or pkgname == 'package2')

class Test_ArchChanges(DownloadEventTestCase):
  "Test arch changes in <main/>"
  def __init__(self, distro, version, arch):
    DownloadEventTestCase.__init__(self, distro, version, arch)
    rxml.tree.uElement('arch', self.conf.get('/distribution/main'), text='i386')

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

def make_suite(distro, version, arch):
  _run_make(pps.path(__file__).dirname)

  suite = ModuleTestSuite('download')

  suite.addTest(make_core_suite(DownloadEventTestCase, distro, version, arch))
  suite.addTest(Test_PackagesDownloaded(distro, version, arch))
  suite.addTest(Test_AddedPackageDownloaded(distro, version, arch))
  suite.addTest(Test_RemovedPackageDeleted(distro, version, arch))
  suite.addTest(Test_ArchChanges(distro, version, arch))
  suite.addTest(Test_MultipleReposWithSamePackage(distro, version, arch))

  return suite
