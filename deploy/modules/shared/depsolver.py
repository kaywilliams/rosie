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
import re
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
                                        'excluded-packages', 'rpmbuild-data'])
    self.depsolve_repo = self.mddir / 'depsolve.repo'

  def setup(self):
    self.all_packages = self.cvars['comps-object'].all_packages
    self.user_required = self.cvars.get('user-required-packages', [])
    self.excluded_packages = self.cvars.get('excluded-packages', [])

    self.rpm_required = [] 
    for v in self.cvars.get('rpmbuild-data', {}).values():
      self.rpm_required.extend(v.get('rpm-requires', []))

    self.DATA['variables'].extend(['all_packages', 'user_required',
                                   'excluded_packages', 'rpm_required',
                                   'depsolver_mixin_version'])

  def resolve(self):
    self._create_repoconfig()

    solver = DeployDepsolver(
      user_required = self.user_required,
      rpm_required = self.rpm_required,
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
  def __init__(self, comps=None, user_required=[], rpm_required=[],
               config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
               logger=None):
    Depsolver.__init__(self,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = PkglistCallback(logger)
    )
    self._comps = comps

    self.user_required = user_required[:]
    self.rpm_required = rpm_required
    self.logger = logger

  def setup(self):
    Depsolver.setup(self)

  def _getGroups(self):
    return self._comps

  def getPackageObjects(self):
    if self.logger: inscb = TimerCallback(self.logger)
    else:           inscb = None

    # Lock user-required and rpm-required packages to a specific
    # version-release if specified as 'name-verion-release', 'name =
    # version-release', or name = epoch:version-release (or variants of the
    # latter two). This works only for packages/rpms we know about (i.e.
    # specified in packages, config-rpms and srpmbuild modules). Kudos to
    # versionlock plugin for showing the way with PackageExcluders. 
    # Ideally we would have a general solution to lock versions every time a
    # package requires a lower version of a dependent package. This would be
    # slow as we'd need to redepsolve on each lock. We could speed it up by
    # caching locks per package (maybe use yum caching in some way for this?)
    # For now we'll stick with a solution that handles the common cases and
    # consider options as needed/available in the future.
    self.locked = {} 
    for pattern in self.user_required + self.rpm_required:
      p = self._get_lock_pattern(pattern)
      nevrs = [ (x.name, x.epoch, x.version, x.release) for x in 
                 self.pkgSack.returnPackages(patterns=[p]) ]
      if len(set(nevrs)) == 1:
        n,e,v,r = nevrs[0]
      else:
        continue

      if '%s-%s-%s' % (n,v,r) == p and n not in self.locked:
        self.logger.log(4, L1("locking %s at version: %s-%s" % (n,v,r)))

        fn = self.pkgSack.addPackageExcluder
        fn(None, '%s1' % n, 'wash.marked')
        fn(None, '%s2' % n, 'mark.name.in', [n])
        fn(None, '%s3' % n, 'wash.nevr.in', ['%s-%s:%s-%s' % (n,e,v,r)])
        fn(None, '%s4' % n, 'exclude.marked')

        self.locked[n] = '%s-%s' % (v,r)

    # install user-required packages
    toinstall = self.user_required[:]
    for pattern in toinstall:
      try:
        txmbr = self.install(pattern=pattern)
      except yum.Errors.InstallError, e:
        lock_msg = self._get_lock_msg(pattern)
        if lock_msg:
          msg = ("unable to install %s%s" % (pattern, lock_msg))
        else:
          msg = e
        raise yum.Errors.InstallError(msg)
      if txmbr:
        self.user_required.remove(pattern)

        for p in txmbr:
          if not pattern.startswith('-'): # ignore deselect patterns
            self.user_required.append(p.name)
            self._comps.return_group('core').mandatory_packages[p.name] = 1

    # install core group
    self.install_errors = []
    self.selectGroup('core', enable_group_conditionals=True)

    # ignore install errors for non user-required packages since
    # some groups have arch specific packages, e.g. s390utils
    missing = set(self.user_required) & set(self.install_errors)
    if missing:
      raise yum.Errors.InstallError("No packages provide '%s'" % 
                                    ', '.join(missing))

    # depsolve
    retcode, errors = self.resolveDeps()

    messages = []
    for e in errors:
      m = re.match('.* requires (.*)', e)
      if m:
        lock_msg = self._get_lock_msg(m.group(1))
        if lock_msg:
          messages.append("%s%s" % (e, lock_msg))
        else:
          messages.append(e)
      else:
        messages.append(e)

    if retcode == 1:
      raise DepsolveError('\n--> '.join(messages))

    return [ x.po for x in self.tsInfo.getMembers() ]

  def _get_lock_pattern(self, pattern):
    return re.sub(r' *==? *([0-9]*:)?', '-', pattern)

  def _get_lock_msg(self, pattern):
    p = self._get_lock_pattern(pattern)
    parts = p.split('-')
    if len(parts) < 3:
      return None

    n = '-'.join(parts[:-2])
    if n in self.locked:
      return ': %s locked at version %s' % (n, self.locked[n])
    else:
      return None
    

class Package:
  def __init__(self, name, arch, remote_path, size, time, checksum):
    self.name = name
    self.arch = arch
    self.remote_path = remote_path
    self.size = size
    self.time = time
    self.checksum = checksum
