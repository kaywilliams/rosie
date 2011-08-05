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
import cPickle
import rpmUtils
import yum

from systemstudio.util import difftest
from systemstudio.util import pps

from systemstudio.util.depsolver import Depsolver

from systemstudio.callback import PkglistCallback, TimerCallback
from systemstudio.sslogging  import L1

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
  def __init__(self):
    self.depsolve_repo = self.mddir / 'depsolve.repo'

  def resolve(self):
    self._create_repoconfig()

    required_packages = self._get_required_packages()
    user_required     = self._get_user_required_packages()
    old_packages      = self._get_old_packages()

    comps_conditional_pkgs = []
    comps_default_pkgs     = []
    comps_mandatory_pkgs   = []
    comps_optional_pkgs    = []

    for group in self.cvars['comps-object'].groups:
      comps_default_pkgs.extend(group.default_packages.keys())
      comps_mandatory_pkgs.extend(group.mandatory_packages.keys())
      comps_optional_pkgs.extend(group.optional_packages.keys())

      # get the package and its requires in the list
      comps_conditional_pkgs.extend([
        (x, y) for x, y in group.conditional_packages.items()
      ])

    solver = IDepsolver(
      all_packages = required_packages,
      old_packages = old_packages or [],
      required = user_required,
      comps_optional_pkgs = comps_optional_pkgs,
      comps_mandatory_pkgs = comps_mandatory_pkgs,
      comps_defaults_pkgs = comps_default_pkgs,
      comps_conditional_pkgs = comps_conditional_pkgs,
      config = str(self.depsolve_repo),
      root = str(self.dsdir),
      arch = self.arch,
      logger = self.logger
    )

    solver.setup()

    solver.comps_pkgs = [ solver.getBestAvailablePackage(n) for n in 
                          comps_mandatory_pkgs + \
                          comps_default_pkgs ]

    pos = solver.getPackageObjects()
    pkgdict = {}
    for po in pos:
      if not pkgdict.has_key(po.repoid):
        pkgdict[po.repoid] = []
      pkgdict[po.repoid].append( (po.name, po.arch, po.remote_path,
                                  po.size, po.filetime) )

    solver.teardown()
    solver = None
    return pkgdict

  def _get_old_packages(self):
    old_packages = []
    difftup = self.diff.variables.difference('cvars[\'all-packages\']')
    if difftup:
      prev, curr = difftup
      if ( prev is None or
           isinstance(prev, difftest.NewEntry) or
           isinstance(prev, difftest.NoneEntry) ):
        prev = []
      if prev:
        old_packages.extend([ x for x in prev if x not in curr ])
    return old_packages

  def _get_required_packages(self):
    return self.cvars.get('all-packages', [])

  def _get_user_required_packages(self):
    return self.cvars.get('user-required-packages', [])

  def _create_repoconfig(self):
    if self.depsolve_repo.exists():
      self.depsolve_repo.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    if self.cvars['excluded-packages']:
      line = 'exclude=' + ' '.join(self.cvars['excluded-packages'])
      conf.append(line)
    for repo in self.cvars['repos'].values():
      conf.extend(repo.lines(pretty=True, baseurl=repo.localurl, mirrorlist=None))
      conf.append('\n')
    self.depsolve_repo.write_lines(conf)


class IDepsolver(Depsolver):
  def __init__(self, all_packages=None, old_packages=None, required=None,
               comps_optional_pkgs=None, comps_mandatory_pkgs=None,
               comps_defaults_pkgs=None, comps_conditional_pkgs=None,
               config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
               logger=None):
    Depsolver.__init__(self,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = PkglistCallback(logger, reqpkgs=required)
    )
    self.all_packages = all_packages
    self.old_packages = old_packages
    self.required = required
    self.logger = logger

    self.comps_optional_pkgs = comps_optional_pkgs or []
    self.comps_mandatory_pkgs = comps_mandatory_pkgs or []
    self.comps_defaults_pkgs = comps_defaults_pkgs or []
    self.comps_conditional_pkgs = comps_conditional_pkgs or []

    self._new_packages = None
    self._cached_file  = None
    self._cached_items = None
    self._installed_packages = None

  @property
  def new_packages(self):
    if self._new_packages is not None:
      return self._new_packages
    self._new_packages = {}
    return self._new_packages

  @property
  def cached_file(self):
    if self._cached_file is not None:
      return self._cached_file
    self._cached_file = pps.path(self.root) / 'cache'
    return self._cached_file

  @property
  def cached_items(self):
    if self._cached_items is not None:
      return self._cached_items
    self._cached_items = {}
    if self.cached_file.exists():
      f = self.cached_file.open('r')
      self._cached_items = cPickle.load(f)
      f.close()
    return self._cached_items

  @property
  def installed_packages(self):
    if self._installed_packages is not None:
      return self._installed_packages
    self._installed_packages = {}
    for pkgtup, deps in self.cached_items.items():
      for tup in [pkgtup] + deps.values():
        if tup not in self._installed_packages:
          try:
            self._installed_packages[tup] = self.getPackageObject(tup)
          except yum.Errors.DepError, e:
            # If one of the deps is missing, remove that dep.  This
            # will cause all the packages requiring this dep to get
            # depsolve'd but the other deps will not be "lost."
            if tup[0] not in self.old_packages and tup[0] not in self.all_packages:
              self.old_packages.append(tup[0])
    return self._installed_packages

  def setup(self):
    Depsolver.setup(self)

  def getPackagesAndDeps(self, packages):
    allpkgtups = set()
    for pkgtup in self.resolved_deps:
      if pkgtup[0] in packages:
        allpkgtups.add(pkgtup)
        for dep in self.resolved_deps[pkgtup].values():
          allpkgtups.add(dep)

    while True:
      newallpkgtups = allpkgtups

      newitems = set()
      for pkgtup in allpkgtups:
        if pkgtup in self.resolved_deps:
          for dep in self.resolved_deps[pkgtup].values():
            newitems.add(dep)

      allpkgtups = allpkgtups.union(newitems)

      if allpkgtups == newallpkgtups:
        break

    return sorted([ x[0] for x in allpkgtups])

  def _provideToPkg(self, req):
    best = None
    (r,f,v) = req

    satisfiers = set()
    for po in self.whatProvides(r,f,v):
      if po not in satisfiers:
        satisfiers.add(po)

    # Minimize packages in the system distribution by giving preference to 
    # satisfiers listed as comps packages
    comps_satisfiers = [ po for po in satisfiers \
                         if po in self.comps_pkgs ]
    if len(comps_satisfiers) > 0:
      satisfiers = comps_satisfiers

    if satisfiers:
      po = self.bestPackagesFromList(satisfiers, arch=self.archstr)[0] 

      thispkgobsdict = self.up.checkForObsolete([po.pkgtup])
      if thispkgobsdict.has_key(po.pkgtup):
        obsoleting = thispkgobsdict[po.pkgtup][0]
        obsoleting_pkg = self.getPackageObject(obsoleting)
        self.deps[req] = obsoleting_pkg
        return obsoleting_pkg
      self.deps[req] = po
      return po
    return None

  def getInstalledPackage(self, name=None, ver=None, rel=None, arch=None, epoch=None):
    for pkgtup_i in self.installed_packages:
      n_i, a_i, e_i, v_i, r_i = pkgtup_i
      pkgtup_o = (name or n_i, arch or a_i, epoch or e_i, ver or v_i, rel or r_i)
      if pkgtup_o == pkgtup_i:
        return self.installed_packages[pkgtup_i]
    return None

  def getDeps(self, pkgtup):
    processed = {}
    rtn = set()
    pkgtups = [pkgtup]
    while pkgtups:
      pkgtup = pkgtups.pop()
      processed[pkgtup] = None
      rtn.add(pkgtup)
      if pkgtup in self.cached_items:
        for x in self.cached_items[pkgtup].values():
          if x not in processed:
            pkgtups.append(x)
    return list(rtn)

  def removePackages(self, pkgtup, isupdated=False):
    if ( isupdated and pkgtup in self.cached_items ):
      instpos = set()
      bestpos = set()
      deps = set(self.cached_items[pkgtup].values())
      for dep in deps:
        if dep == pkgtup:
          continue
        n,a,e,v,r = dep
        instpo = self.getInstalledPackage(name=n, arch=a, epoch=e, ver=v, rel=r)
        bestpo = self.getBestAvailablePackage(name=n, arch=a)
        if instpo: instpos.add(instpo)
        if bestpo: bestpos.add(bestpo)
      if instpos == bestpos:
        if pkgtup in self.installed_packages:
          del self.installed_packages[pkgtup]
        if pkgtup in self.cached_items:
          del self.cached_items[pkgtup]
        return [pkgtup]

    removed = []
    pkgtups = self.getDeps(pkgtup)
    for pkgtup in pkgtups:
      removed.append(pkgtup)
      if pkgtup in self.installed_packages:
        del self.installed_packages[pkgtup]
      if pkgtup in self.cached_items:
        del self.cached_items[pkgtup]
    return removed

  def installPackage(self, po):
    self.installed_packages[po.pkgtup] = po

  def getPackageObjects(self):
    if self.logger: inscb = TimerCallback(self.logger)
    else:           inscb = None

    if inscb: inscb.start("checking for package changes")
    self.iremove()
    self.iinstall()
    self.iupdate()
    if inscb: inscb.end()

    if self.logger: self.logger.log(1, L1("resolving package dependencies"))
    for po in self.installed_packages.values():
      self.install(po=po)

    # build a list of TransactionMember objects that need to have
    # their dependencies resolved. They are added to the list of
    # 'unresolved' packages if they have one or more their deps
    # missing, or have no deps at all.
    unresolved = []
    for txmbr in self.tsInfo.getMembers():
      resolved = True
      if txmbr.po.pkgtup in self.cached_items:
        for dep in self.cached_items[txmbr.po.pkgtup].values():
          if not self.tsInfo.exists(pkgtup=dep):
            resolved = False
            break
      else:
        resolved = False

      if not resolved:
        unresolved.append(txmbr)
      else:
        # if dependencies are resolved, add to Depsolver.final_pkgobjs
        # and add entry in Depsolver.resolved_deps, so that the data
        # is cached for the next time pkglist is run.
        try:
          self.resolved_deps[txmbr.po.pkgtup] = self.cached_items[txmbr.po.pkgtup]
        except KeyError:
          # should never happen, but you never know :(. If exception
          # is raised don't mark package as resolved.
          pass
        else:
          self.final_pkgobjs[txmbr.po] = None

    pos = Depsolver.getPackageObjects(self, unresolved=unresolved)

    f = self.cached_file.open('wb')
    cPickle.dump(self.resolved_deps, f, -1)
    f.close()

    return pos

  def iremove(self):
    # handle obsolete packages
    if not self.old_packages: return

    for pkg in self.old_packages:
      for pkgtup in self.cached_items:
        if pkgtup[0] == pkg:
          self.removePackages(pkgtup)
          break

  def iinstall(self):
    # handle new packages
    if not self.all_packages: return

    for package in self.all_packages:
      instpo = self.getInstalledPackage(name=package)
      bestpo = self.getBestAvailablePackage(name=package)
      if instpo is None:
        if bestpo is None and package in self.required:
          raise yum.Errors.InstallError("No packages provide '%s'" % package)
        elif bestpo is not None:
          self.installPackage(bestpo)
          self.new_packages[bestpo] = None

  def iupdate(self):
    if not self.installed_packages: return

    removed = set()
    for pkgtup, po in self.installed_packages.items():
      if po in self.new_packages or pkgtup in removed:
        continue

      bestpo = self.getBestAvailablePackage(name=pkgtup[0], arch=pkgtup[1])
      if po and bestpo and po != bestpo:
        # make sure that all the packages requiring the old package
        # can now require the new package seamlessly. First, we check
        # all the packages that require the old package, and make a
        # note of what it is about the old package that the package
        # requires. Then we check to make sure that the new package
        # provides that same exact thing. If it doesn't, then the new
        # package cannot replace the old package.
        requirements = []
        for package, deps in self.cached_items.items():
          for req, dep in deps.items():
            if dep == po.pkgtup:
              requirements.append(req)

        if satisfies_requirements(bestpo, requirements):
          if po:
            for x in self.removePackages(po.pkgtup, isupdated=True):
              removed.add(x)
          if bestpo:
            self.installPackage(bestpo)


def satisfies_requirements(po, requirements):
  """
  Return true if the package object provides everything in the list of
  requirements.
  """
  pkg_satisfies_reqs = True
  for req in requirements:
    if req in po.provides or \
        ( req[0].startswith('/') and req[0] in po.filelist ):
      continue

    # if the best package satisfies the requirement and some,
    # continue
    for prov in po.provides:
      if rpmUtils.miscutils.rangeCompare(req, prov):
        break
    else:
      # if you get here, it means that the "new" package doesn't
      # provide everything the "old" package did.
      pkg_satisfies_reqs = False
      break
  return pkg_satisfies_reqs
