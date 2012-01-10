#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
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

from centosstudio.callback  import PkglistCallback
from centosstudio.constants import KERNELS
from centosstudio.errors    import assert_file_has_content, CentOSStudioError
from centosstudio.event     import Event
from centosstudio.cslogging   import L1

from centosstudio.modules.shared.depsolver import DepsolverMixin
from centosstudio.util.depsolver.depsolver import DepsolveError

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
      provides = ['groupfile', 'pkglist'],
      requires = ['repos'], #extended in Depsolver mixin
      conditionally_requires = [], # set in Depsolver Mixin
      version = '1.08'
    )

    DepsolverMixin.__init__(self)

    self.dsdir = self.mddir / 'depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['.'],
      'variables': [],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    DepsolverMixin.setup(self)

    self.compsfile = self.mddir/'comps.xml'
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
    # write comps.xml
    self.compsfile.write_text(self.cvars['comps-object'].xml())
    self.compsfile.chmod(0644)
    self.DATA['output'].append(self.compsfile)

    # create pkglist
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    self._clean_dsdir()

    try:
      pkgs_by_repo = self.resolve() # in DepsolverMixin
    except (DepsolveError, yum.Errors.InstallError), e:
      raise CentOSStudioDepsolveError(str(e))

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
    # set groupfile cvars
    self.cvars['groupfile'] = self.compsfile
    assert_file_has_content(self.cvars['groupfile'])

    # set pkglist cvars
    assert_file_has_content(self.pkglistfile)
    pklfile = open(self.pkglistfile, 'rb')
    self.cvars['pkglist'] = cPickle.load(pklfile)
    pklfile.close()

  def verify_cvar_comps_file(self):
    "cvars['groupfile'] exists"
    self.verifier.failUnless(self.cvars['groupfile'].exists(),
      "unable to find comps.xml file at '%s'" % self.cvars['groupfile'])

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


class InvalidPkglistFormatError(CentOSStudioError):
  message = ( "Invalid format '%(pkgfile)s' on line %(lino)d of "
              "pkglist '%(line)s'.\n\nFormat should "
              "be %{NAME}-%{VERSION}-%{RELEASE}-%{ARCH}" )

class CentOSStudioDepsolveError(CentOSStudioError):
  message = ( "Error(s) resolving package dependencies: \n"
              "--> %(message)s" )
