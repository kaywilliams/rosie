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
import cPickle
import rpmUtils
import yum

from deploy.util import difftest

from deploy.util.depsolver import Depsolver
from deploy.util.depsolver.depsolver import DepsolveError

from deploy.callback import PkglistCallback, TimerCallback
from deploy.dlogging  import L1
from deploy.main     import ARCH_MAP

YUMCONF_HEADER = [
  '[main]',
  'cachedir=',
  'logfile=/depsolve.log',
  'debuglevel=0',
  'errorlevel=0',
  'gpgcheck=0',
  'tolerant=1',
  'exactarch=1',
  'reposdir=/',
  '\n',
]

class DepsolverMixin(object):
  depsolver_mixin_version = "1.01"

  def __init__(self, *args, **kwargs):
    self.requires.update(['comps-object'])
    self.conditionally_requires.update(['user-required-packages', 
                                        'excluded-packages'])
    self.depsolve_repo = self.mddir / 'depsolve.repo'

  def setup(self):
    self.all_packages = self.cvars['comps-object'].all_packages
    self.user_required = self.cvars.get('user-required-packages', [])
    self.excluded_packages = self.cvars.get('excluded-packages', [])
    self.DATA['variables'].extend(['all_packages', 'user_required',
                                   'excluded_packages', 
                                   'depsolver_mixin_version'])

  def resolve(self):
    self._create_repoconfig()

    solver = DeployDepsolver(
      user_required = self.user_required,
      comps = self.cvars['comps-object'],
      config = str(self.depsolve_repo),
      root = str(self.dsdir),
      arch = ARCH_MAP[self.arch],
      logger = self.logger
    )

    try:
      solver.setup()

      pos = solver.getPackageObjects()
      pkgs = [ po.name for po in pos ]

      pkgdict = {}
      for po in pos:
        pkgdict.setdefault(po.repoid, {})[po.name] = Package(
          po.name, po.arch, po.remote_path, po.size, po.filetime, po.checksum)

    finally:
      solver.teardown()
      solver = None

    return pkgdict

  def _create_repoconfig(self):
    if self.depsolve_repo.exists():
      self.depsolve_repo.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    conf.append('installroot=%s' % self.dsdir) 
    conf.append('persistdir=%s/var/lib/yum' % self.dsdir) 
    conf.append('releasever=%s' % self.version) 
    if self.excluded_packages:
      line = 'exclude=' + ' '.join(self.excluded_packages)
      conf.append(line)
    for repo in self.cvars['repos'].values():
      conf.extend(repo.lines(pretty=True, baseurl=repo.localurl, mirrorlist=None))
      # ensure our packages are not overridden by packages from other repos
      # TODO - add a test case
      if not repo.id == self.build_id:
        line = 'exclude=' + ' '.join(self.cvars['rpmbuild-data'].keys())
        conf.append(line)
      conf.append('\n')
    self.depsolve_repo.write_lines(conf)


class DeployDepsolver(Depsolver):
  def __init__(self, comps=None, user_required=None, 
               config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
               logger=None):
    Depsolver.__init__(self,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = PkglistCallback(logger)
    )
    self._comps = comps

    self.user_required = user_required
    self.logger = logger

  def setup(self):
    Depsolver.setup(self)

  def _getGroups(self):
    return self._comps

  def getPackageObjects(self):
    if self.logger: inscb = TimerCallback(self.logger)
    else:           inscb = None

    self.install_errors = []
    self.selectGroup('core', enable_group_conditionals=True)
    missing = set(self.user_required) & set(self.install_errors)
    if missing:
      raise yum.Errors.InstallError("No packages provide '%s'" % 
                                    ', '.join(missing))

    retcode, errors = self.resolveDeps()

    if retcode == 1:
      raise DepsolveError('\n--> '.join(errors))

    return [ x.po for x in self.tsInfo.getMembers() ]

class Package:
  def __init__(self, name, arch, remote_path, size, time, checksum):
    self.name = name
    self.arch = arch
    self.remote_path = remote_path
    self.size = size
    self.time = time
    self.checksum = checksum
