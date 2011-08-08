#
# Copyright (c) 2011
# OpenProvision, Inc. All rights reserved.
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
import cPickle
import re
import rpmUtils.arch
import yum.Errors

from openprovision.callback  import PkglistCallback
from openprovision.constants import KERNELS
from openprovision.errors    import assert_file_has_content, OpenProvisionError
from openprovision.event     import Event
from openprovision.sslogging   import L1

from openprovision.modules.shared.idepsolver import DepsolverMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['DepsolveEvent'],
  description = 'depsolves required packages and groups to create a package list',
  group       = 'repocreate',
)

NVRA_REGEX = re.compile('(?P<name>.+)'    # rpm name
                        '-'
                        '(?P<version>.+)' # rpm version
                        '-'
                        '(?P<release>.+)' # rpm release
                        '\.'
                        '(?P<arch>.+)')   # rpm architecture

class DepsolveEvent(Event, DepsolverMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'depsolve',
      parentid = 'repocreate',
      provides = ['pkglist'],
      requires = ['comps-object', 'repos', 'all-packages', 'comps-group-info',
                  'user-required-packages'],
      conditionally_requires = ['excluded-packages'],
      version = '1.07'
    )

    DepsolverMixin.__init__(self)

    self.dsdir = self.mddir / 'depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'all-packages\']',
                    'cvars[\'comps-group-info\']',
                    'cvars[\'user-required-packages\']',
                    'cvars[\'excluded-packages\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.pkglistfile = self.mddir / 'pkglist'

    # add relevant input/variable sections
    for repoid, repo in self.cvars['repos'].items():
      for attr in ['baseurl', 'mirrorlist', 'exclude',
                   'includepkgs', 'enabled']:
        if getattr(repo, attr):
          self.DATA['variables'].append('cvars[\'repos\'][\'%s\'].%s'
                                        % (repoid, attr))

      for subrepo in repo.subrepos.values():
        self.DATA['input'].append(repo.localurl/subrepo._relpath/'repodata')

  def run(self):
    # create pkglist
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    self._clean_dsdir()

    try:
      pkgs_by_repo = self.resolve() # in DepsolverMixin
    except yum.Errors.InstallError, e:
      raise DepsolveError(str(e))

    count = 0
    for tups in pkgs_by_repo.itervalues():
      count = count + len(tups)
    self.log(1, L1("pkglist closure achieved in %d packages" % count))

    self.log(1, L1("writing pkglist"))
    pklfile = self.pkglistfile.open('wb')
    cPickle.dump(pkgs_by_repo, pklfile, -1)
    pklfile.close()

    self.DATA['output'].extend([self.dsdir, self.pkglistfile,
                                self.depsolve_repo])

  def apply(self):
    self.io.clean_eventcache()
    assert_file_has_content(self.pkglistfile)
    pklfile = open(self.pkglistfile, 'rb')
    self.cvars['pkglist'] = cPickle.load(pklfile)
    pklfile.close()

  def verify_pkglistfile_exists(self):
    "pkglist file exists"
    self.verifier.failUnlessExists(self.pkglistfile)

  def verify_pkglistfile_has_content(self):
    "pkglist file has content"
    if self.cvars['pkglist']:
      self.verifier.failUnless(len(self.cvars['pkglist']) > 0,
                               "pkglist is empty")
    else:
      self.verifier.fail("pkglist is empty")

  def verify_kernel_arch(self):
    "kernel arch matches arch in config"
    matched = False
    pkgs = []
    for v in self.cvars['pkglist'].itervalues():
      pkgs.extend(v)
    for pkg in pkgs:
      try:
        n,a,__,_,_ = pkg
        if n not in KERNELS: continue
        self.verifier.failUnlessEqual(rpmUtils.arch.getBaseArch(a), self.basearch,
          "the base arch of kernel package '%s' does not match the specified "
          "base arch '%s'" % (pkg, self.basearch))
        matched = True
      except AttributeError:
        pass

    self.verifier.failUnless(matched, "no kernel package found")

  def _clean_dsdir(self):
    for f in self.diff.variables.difference().keys():
      if f.startswith('cvars[\'repos\']'):
        self.dsdir.rm(recursive=True, force=True)
        break


class InvalidPkglistFormatError(OpenProvisionError):
  message = ( "Invalid format '%(pkgfile)s' on line %(lino)d of "
              "pkglist '%(line)s'.\n\nFormat should "
              "be %{NAME}-%{VERSION}-%{RELEASE}-%{ARCH}" )

class DepsolveError(OpenProvisionError):
  message = "Error resolving package dependencies: %(message)s"
