#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

from centosstudio.errors import CentOSStudioError

from centosstudio.util import pps
from centosstudio.util import repo
from centosstudio.util import rxml
from centosstudio.util.repo import RPM_PNVRA_REGEX
from centosstudio.util.pps.constants import TYPE_NOT_DIR

from cstest      import EventTestCase, ModuleTestSuite, _run_make
from cstest.core import make_core_suite


class DownloadEventTestCase(EventTestCase):
  moduleid = 'download'
  eventid  = 'download'

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
  def runTest(self):
    self.execute_predecessors(self.event)
    self.event.setup()
    self.event._process_keys()
    self.event._process_packages()
    # if the length of rpms in the pkglist is equal to the length of
    # rpms in list_output, then we know for that we are not downloading 
    # duplicate packages.
    pkglist = []
    downloaded = []
    for subrepo in self.event.cvars['pkglist']:
      pkglist.extend(self.event.cvars['pkglist'][subrepo])
      downloaded.extend(self.event.io.list_output(what=subrepo))
    self.failUnless(len(pkglist) == len(downloaded))


class Test_FailsOnUnsignedPackages(DownloadEventTestCase):
  "fails on unsigned packages"

  # create shared test repos
  _run_make(pps.path(__file__).dirname/'shared')

  # add an unsigned package
  _conf = """<packages>
    <package>package1</package>
  </packages>"""

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(CentOSStudioError, self.event)

class Test_FailsIfKeyNotProvided(DownloadEventTestCase):
  "fails if no keys defined"

  def _make_repos_config(self):
    repos = rxml.config.Element('repos')
    base = repo.getDefaultRepoById('base', distro=self.distro,
           version=self.version, arch=self.arch, include_baseurl=True,
           baseurl='http://www.centossolutions.com/mirrors/%s' % self.distro)
    # set gpgkeys to none
    base.update({'mirrorlist': None, 'gpgkey': None, 'gpgcheck': None,})
    repos.append(base.toxml())
    return repos

  def setUp(self):
    EventTestCase.setUp(self)
    self.clean_event_md()

  def runTest(self):
    self.execute_predecessors(self.event)
    self.failUnlessRaises(CentOSStudioError, self.event)

class Test_CompsFile(DownloadEventTestCase):
  "comps file included in repodata"
  def runTest(self):
    self.tb.dispatch.execute(until=self.id)
    self.failUnlessExists(self.event.rpmsdir / 'repodata' /
                          self.event.cvars['groupfile'].basename)

def make_suite(distro, version, arch, *args, **kwargs):
  _run_make(pps.path(__file__).dirname/'shared')

  suite = ModuleTestSuite('download')

  suite.addTest(make_core_suite(DownloadEventTestCase, distro, version, arch))
  suite.addTest(Test_PackagesDownloaded(distro, version, arch))
  suite.addTest(Test_AddedPackageDownloaded(distro, version, arch))
  suite.addTest(Test_RemovedPackageDeleted(distro, version, arch))
  suite.addTest(Test_MultipleReposWithSamePackage(distro, version, arch))
  suite.addTest(Test_FailsOnUnsignedPackages(distro, version, arch))
  suite.addTest(Test_FailsIfKeyNotProvided(distro, version, arch))
  suite.addTest(Test_CompsFile(distro, version, arch))

  return suite
