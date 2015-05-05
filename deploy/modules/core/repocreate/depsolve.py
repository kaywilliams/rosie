#
# Copyright (c) 2015
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
import re
import rpmUtils.arch
import yum.Errors

from deploy.callback  import PkglistCallback
from deploy.constants import KERNELS
from deploy.errors    import assert_file_has_content, DeployEventError
from deploy.event     import Event
from deploy.dlogging import L1

from deploy.modules.shared import DepsolverMixin, ShelveMixin

from deploy.util.depsolver.depsolver import DepsolveError

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['DepsolveEvent'],
    description = 'depsolves required packages and groups to create a package list',
    group       = 'repocreate',
  )


class DepsolveEvent(DepsolverMixin, ShelveMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'depsolve',
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['pkglist'],
      requires = ['repos'], #extended in Depsolver mixin
      conditionally_requires = [], # set in Depsolver Mixin
      version = '1.10'
    )

    self.publish_module = 'publish'
    DepsolverMixin.__init__(self)

    self.dsdir = self.mddir / 'depsolve'

    self.DATA = {
      'config':    set(['.']),
      'variables': set(),
      'input':     set(),
      'output':    set(),
    }

    ShelveMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    DepsolverMixin.setup(self)

    self.pkglistfile = self.mddir / 'pkglist'

    # add relevant input/variable sections
    for repoid, repo in self.cvars['repos'].items():
      for attr in ['baseurl', 'mirrorlist', 'exclude',
                   'include', 'enabled']:
        if getattr(repo, attr):
          self.DATA['variables'].add('cvars[\'repos\'][\'%s\'].%s'
                                        % (repoid, attr))

      for subrepo in repo.subrepos.values():
        self.DATA['input'].add(repo.localurl/subrepo._relpath/'repodata')

  def run(self):
    # create pkglist
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    self._clean_dsdir()

    try:
      pkgs_by_repo = self.resolve() # in DepsolverMixin
    except (DepsolveError, yum.Errors.InstallError), e:
      raise DeployDepsolveError(str(e))

    count = 0
    for tups in pkgs_by_repo.itervalues():
      count = count + len(tups)
    self.log(1, L1("pkglist closure achieved in %d packages" % count))

    self.log(1, L1("writing pkglist"))
    self.shelve('pkglist', pkgs_by_repo)

    self.DATA['output'].update([self.dsdir])

    # generate comps.xml
    DepsolverMixin.run(self)

  def apply(self):
    # set pkglist cvars
    self.cvars['pkglist'] = self.unshelve('pkglist', {})

  def verify_pkglistfile_has_content(self):
    "pkglist file has content"
    if self.cvars['pkglist']:
      self.verifier.failUnless(len(self.cvars['pkglist']) > 0,
                               "pkglist is empty")
    else:
      self.verifier.fail("pkglist is empty")

  def verify_kernel_arch(self):
    "kernel arch matches arch in config"

    if not self.type == 'system': return

    matched = False
    pkgs = []
    for repo in self.cvars['pkglist'].itervalues():
      pkgs.extend(repo.values())
    for pkg in pkgs:
      if pkg.name not in KERNELS: continue
      self.verifier.failUnlessEqual(rpmUtils.arch.getBaseArch(pkg.arch),
        self.arch,
        "the base arch of kernel package '%s' does not match the specified "
        "base arch '%s'" % (pkg.name, self.arch))
      matched = True
   
    self.verifier.failUnless(matched, "no kernel package found")

  def _clean_dsdir(self):
    # clean the depsolve dir if repos have been added or removed, etc.
    for f in self.diff.variables.difference().keys():
      if f.startswith('cvars[\'repos\']'):
        self.dsdir.rm(recursive=True, force=True)
        return

    # or if repodata files have changed
    for f in self.diff.input.difference().keys():
      for url in [ x.localurl for x in self.cvars['repos'].values()]:
        if f.startswith(url):
          self.dsdir.rm(recursive=True, force=True)
          return

class InvalidPkglistFormatError(DeployEventError):
  message = ( "Invalid format '%(pkgfile)s' on line %(lino)d of "
              "pkglist '%(line)s'.\n\nFormat should "
              "be %{NAME}-%{VERSION}-%{RELEASE}-%{ARCH}" )

class DeployDepsolveError(DeployEventError):
  message = ( "Error(s) resolving package dependencies: \n"
              "--> %(message)s" )
