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
import cPickle
import rpmUtils
import yum

from rendition import pps

from rendition.depsolver import Depsolver

from spin.callback import IDepsolverCallback
from spin.logging  import L1

def resolve(all_packages=None, old_packages=None, required=None,
            config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
            callback=None, logger=None):
  solver = IDepsolver(
             all_packages = all_packages,
             old_packages = old_packages,
             required = required,
             config = config,
             root = root,
             arch = arch,
             callback = callback,
             logger = logger
           )
  solver.setup()
  pos = solver.getPackageObjects()
  pkgtups = [ po.pkgtup for po in pos ]
  solver.teardown()
  return pkgtups

class IDepsolver(Depsolver):
  def __init__(self, all_packages=None, old_packages=None, required=None,
               config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
               callback=None, logger=None):
    Depsolver.__init__(self,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = callback
    )
    self.all_packages = all_packages
    self.old_packages = old_packages
    self.required     = required

    self.new_packages = {}
    self.installed_packages = {}

    self.cached_file = pps.path(root) / 'cache'
    self.cached_items = {}

    self.logger = logger

  def setup(self):
    Depsolver.setup(self)

    if self.cached_file.exists():
      f = self.cached_file.open('r')
      self.cached_items = cPickle.load(f)
      f.close()
      for pkgtup, deps in self.cached_items.items():
        for tup in [pkgtup] + deps.values():
          if self.installed_packages.has_key(tup):
            continue
          try:
            self.installed_packages[tup] = self.getPackageObject(tup)
          except yum.Errors.DepError, e:
            # If one of the deps is missing, remove that dep.  This
            # will cause all the packages requiring this dep to get
            # depsolve'd but the other deps will not be "lost."
            if tup[0] not in self.old_packages and tup[0] not in self.all_packages:
              self.old_packages.append(tup[0])

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
      if self.cached_items.has_key(pkgtup):
        for x in self.cached_items[pkgtup].values():
          if not processed.has_key(x):
            pkgtups.append(x)
    return list(rtn)

  def removePackages(self, pkgtup, isupdated=False):
    if ( isupdated and self.cached_items.has_key(pkgtup) ):
      instpos = {}
      bestpos = {}
      deps = set([pkgtup] + self.cached_items[pkgtup].values())
      for dep in deps:
        n,a,e,v,r = dep
        instpo = self.getInstalledPackage(name=n, arch=a, epoch=e, ver=v, rel=r)
        bestpo = self.getBestAvailablePackage(name=n)
        if instpo:
          instpos[instpo] = None
        if bestpo:
          bestpos[bestpo] = None
      if instpos == bestpos:
        # all the requires of the package are the same, just delete it and
        # none of its deps
        if self.installed_packages.has_key(pkgtup):
          del self.installed_packages[pkgtup]
        if self.cached_items.has_key(pkgtup):
          del self.cached_items[pkgtup]
        return [pkgtup]

    removed = []
    pkgtups = self.getDeps(pkgtup)
    for pkgtup in pkgtups:
      removed.append(pkgtup)
      if self.installed_packages.has_key(pkgtup):
        del self.installed_packages[pkgtup]
      if self.cached_items.has_key(pkgtup):
        del self.cached_items[pkgtup]
    return removed

  def installPackage(self, po):
    self.installed_packages[po.pkgtup] = po

  def getPackageObjects(self):
    if self.logger: inscb = IDepsolverCallback(self.logger)
    else:           inscb = None

    if inscb: inscb.start("checking for package changes")
    self.iremove()
    self.iinstall()
    self.iupdate()
    if inscb: inscb.end()

    self.logger.log(1, L1("resolving package dependencies"))
    for po in self.installed_packages.values():
      self.install(po=po)

    # build a list of TransactionMember objects that need to have
    # their dependencies resolved. They are added to the list of
    # 'unresolved' packages if they have one or more their deps
    # missing, or have no deps at all.
    unresolved = []
    for txmbr in self.tsInfo.getMembers():
      resolved = True
      if self.cached_items.has_key(txmbr.po.pkgtup):
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

    f = self.cached_file.open('w')
    cPickle.dump(self.resolved_deps, f)
    f.close()

    return pos

  def iremove(self):
    # handle obsolete packages
    if not self.old_packages: return

    for pkg in self.old_packages:
      for pkgtup in self.cached_items.keys():
        if pkgtup[0] == pkg:
          break
        self.removePackages(pkgtup)

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

    removed = []
    for pkgtup, po in self.installed_packages.items():
      if self.new_packages.has_key(po):
        continue
      if pkgtup in removed:
        continue
      bestpo = self.getBestAvailablePackage(name=pkgtup[0])
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
        required = False
        for req in requirements:
          if req not in bestpo.provides:
            if req[0].startswith('/') and req[0] in bestpo.filelist:
              # check to see if the requirement is a file and that the file
              # is in the new package as well
              continue
            if req[0] == pkgtup[0]:
              if req[1] is None:
                continue
              if not (isinstance(req[1], str) or isinstance(req[1], unicode)):
                flag = rpmUtils.miscutils.flagToString(req[1])
              else:
                flag = req[1]
              newpo_evr = (bestpo.pkgtup[2], bestpo.pkgtup[3], bestpo.pkgtup[4])
              reqpo_evr = req[2]
              evr_check = rpmUtils.miscutils.compareEVR(reqpo_evr, newpo_evr)
              if flag == 'LT' and evr_check > 0:
                continue
              if flag == 'LE' and evr_check >= 0:
                continue
              if flag == 'EQ' and evr_check == 0:
                continue
              if flag == 'GE' and evr_check <= 0:
                continue
              if flag == 'GT' and evr_check < 0:
                continue
            required = True
            break
        if required:
          continue

        if po:
          removed.extend(self.removePackages(po.pkgtup, isupdated=True))
        if bestpo:
          self.installPackage(bestpo)
