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
import re
import rpmUtils.arch
import yum.Errors

from spin.callback  import PkglistCallback
from spin.constants import KERNELS
from spin.errors    import assert_file_has_content, SpinError
from spin.event     import Event
from spin.logging   import L1

from spin.modules.shared.idepsolver import DepsolverMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['DepsolveEvent'],
  description = 'depsolves required packages and groups to create a package list',
  group       = 'repository',
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
      parentid = 'repository',
      provides = ['pkglist', 'pkglist-install-packages'],
      requires = ['all-packages', 'repos', 'user-required-packages'],
      conditionally_requires = ['pkglist-excluded-packages'],
      version = '0.2',
    )

    DepsolverMixin.__init__(self)

    self.dsdir = self.mddir / 'depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'all-packages\']',
                    'cvars[\'pkglist-excluded-packages\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.pkglistfile = self.mddir / 'pkglist'

    # add relevant input/variable sections, if interesting
    for repoid, repo in self.cvars['repos'].items():
      for attr in ['baseurl', 'mirrorlist', 'exclude',
                   'includepkgs', 'enabled']:

        if getattr(repo, attr):
          self.DATA['variables'].append('cvars[\'repos\'][\'%s\'].%s'
                                        % (repoid, attr))

      self.DATA['input'].append(repo.localurl/'repodata')

  def run(self):
    # create pkglist
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    self._verify_repos()

    try:
      pkgtups = self.resolve() # in DepsolverMixin
    except yum.Errors.InstallError, e:
      raise DepsolveError(str(e))

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,a,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s.%s' % (n,v,r,a))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    self.pkglistfile.write_lines(pkglist)

    self.DATA['output'].extend([self.dsdir, self.pkglistfile,
                                self.depsolve_repo, self.install_pkgsfile])

  def apply(self):
    self.io.clean_eventcache()
    assert_file_has_content(self.pkglistfile)
    self.cvars['pkglist'] = self.pkglistfile.read_lines()

    # ensure what we read in is comprehensible
    rx = re.compile('(.+)-(.+)-(.+)\.(.+)')
    for i in range(0, len(self.cvars['pkglist'])):
      if not rx.match(self.cvars['pkglist'][i]):
        raise InvalidPkglistFormatError(self.pkglistfile,
                                        i+1, self.cvars['pkglist'][i])

    self.cvars['pkglist-install-packages'] = self.install_pkgsfile.read_lines()

  def verify_pkglistfile_exists(self):
    "pkglist file exists"
    self.verifier.failUnlessExists(self.pkglistfile)

  def verify_pkglistfile_has_content(self):
    "pkglist file has content"
    if self.cvars['pkglist']:
      self.verifier.failUnless(len(self.cvars['pkglist']) > 0,
                               "pkglst is empty")
    else:
      self.verifier.fail("pkglist is empty")

  def verify_kernel_arch(self):
    "kernel arch matches arch in config"
    matched = False
    for pkg in self.cvars['pkglist']:
      try:
        n,v,r,a = NVRA_REGEX.match(pkg).groups()
        if n not in KERNELS: continue
        self.verifier.failUnlessEqual(rpmUtils.arch.getBaseArch(a), self.basearch,
          "the base arch of kernel package '%s' does not match the specified "
          "base arch '%s'" % (pkg, self.basearch))
        matched = True
      except AttributeError:
        pass

    self.verifier.failUnless(matched, "no kernel package found")

  def _verify_repos(self):
    for repoid, repo in self.cvars['repos'].items():
      for f in self.diff.input.difference().keys():
        if f.startswith(repo.localurl/'repodata'):
          (self.dsdir/repoid).rm(recursive=True, force=True)
          break


class InvalidPkglistFormatError(SpinError):
  message = ( "Invalid format '%(pkgfile)s' on line %(lino)d of "
              "pkglist '%(line)s'.\n\nFormat should "
              "be %{NAME}-%{VERSION}-%{RELEASE}-%{ARCH}" )

class DepsolveError(SpinError):
  message = "Error resolving package dependencies: %(message)s"
