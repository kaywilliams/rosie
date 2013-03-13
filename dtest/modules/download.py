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
from deploy.util import pps
from deploy.util import rxml
from deploy.util.repo import RPM_PNVRA_REGEX

from dtest      import EventTestCase, ModuleTestSuite, _run_make
from dtest.core import make_core_suite


class DownloadEventTestCase(EventTestCase):
  moduleid = 'download'
  eventid  = 'download'
  _mode = 'package'

  def _make_repos_config(self):
    repos = EventTestCase._make_repos_config(self)

    rxml.config.Element('repofile', text='shared/test-repos.repo', parent=repos)

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
    self.tb.dispatch.execute(until=self.id)
    for rpm in self.event.io.list_output():
      self.failUnlessExists(rpm)
      _,_,_,_,a = self._deformat(rpm)
      self.failUnless(a in self.event._validarchs)

class Test_PackagesDownloaded(DownloadEventTestCase):
  "Test to see that all packages are downloaded"
  pass

class Test_AddedPackageDownloaded(DownloadEventTestCase):
  "Test that the packages in <packages> are downloaded"
  _conf = [
  """<packages>
    <package>package1</package>
    <package>package2</package>
  </packages>
  """,
  """
  <release-rpm>
    <updates gpgcheck='false'/>
  </release-rpm>
  """]

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

class Test_MultipleReposWithSamePackage(DownloadEventTestCase):
  "Test multiple repos with the same package."
  _mode = 'system' # include pkgs from base and update repos
  _conf = [
  """<packages>
    <package>package1</package>
    <package>package2</package>
  </packages>
  """,
  """
  <release-rpm>
    <updates gpgcheck='false'/>
  </release-rpm>
  """]
  def runTest(self):
    self.tb.dispatch.execute(until=self.id)
    # if the length of rpms in the pkglist is equal to the length of
    # rpms in list_output, then we know for that we are not downloading 
    # duplicate packages.
    pkglist = []
    downloaded = []
    for subrepo in self.event.cvars['pkglist']:
      pkglist.extend(self.event.cvars['pkglist'][subrepo])
      downloaded.extend(self.event.io.list_output(what=subrepo))
    self.failUnless(len(pkglist) == len(downloaded))


def make_suite(os, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('download')

  suite.addTest(make_core_suite(DownloadEventTestCase, os, version, arch))
  suite.addTest(Test_PackagesDownloaded(os, version, arch))
  suite.addTest(Test_AddedPackageDownloaded(os, version, arch))
  suite.addTest(Test_RemovedPackageDeleted(os, version, arch))
  suite.addTest(Test_MultipleReposWithSamePackage(os, version, arch))

  return suite
