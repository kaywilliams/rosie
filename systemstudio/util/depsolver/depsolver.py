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
import rpmUtils.arch
import yum

import logging
logger = logging.getLogger('yum.YumBase')
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
logger.addHandler(handler)

class DepsolveError(yum.Errors.MiscError):
  pass

class SystemStudioYum(yum.YumBase):
  def __init__(self, config='/etc/yum.conf', root='/tmp/depsolver',
               arch=None, callback=None):
    yum.YumBase.__init__(self)
    self.config = config
    self.root = root
    self.archstr = arch
    self.dsCallback = callback

    self._rpmdb = None

  def __del__(self):
    pass

  def doRpmDBSetup(self):
    pass
  def _getRpmDB(self):
    if self._rpmdb is None:
      self._rpmdb = DummyRpmDBPackageSack(self.conf.installroot)
    return self._rpmdb
  rpmdb = property(fget=lambda self:        self._getRpmDB(),
                   fset=lambda self, value: setattr(self, '_rpmdb', value),
                   fdel=lambda self:        setattr(self, '_rpmdb', None))

  def setup(self):
    "Prepare to resolve dependencies by setting up metadata."
    if self.dsCallback: self.dsCallback.setupStart()
    self.preconf.fn = str(self.config)
    self.preconf.root = str(self.root)
    self.preconf.init_plugins = False
    self.doRpmDBSetup()
    self.conf.cache = 0
    self.conf.obsoletes = 1
    self.doRepoSetup()
    self.doSackSetup(archlist=rpmUtils.arch.getArchList(self.archstr))
    self.doTsSetup()
    self.doUpdateSetup()

    # this could be a problem, but is OK for now
    self.repos.populateSack('enabled', 'filelists')
    if self.dsCallback: self.dsCallback.setupEnd()

  def doFileLogSetup(self, *args, **kwargs): pass
  def doLoggingSetup(self, *args, **kwargs): pass
  def getDownloadPkgs(self, *args, **kwargs): pass

  def getBestAvailablePackages(self, name, ver=None, rel=None, arch=None, epoch=None,
                               **kwargs):
    """
    Returns the list of best available packages that meet the
    parameters to this method.  The second return value is a boolean;
    this value is True if the package providing the @param=name
    doesn't have the same name as @param=name.
    """
    name_mismatch = False
    pkgs = self.pkgSack.searchNevra(
             name = name,
             ver = ver,
             rel = rel,
             arch = arch,
             epoch = epoch
           )
    if pkgs:
      pkgSack = yum.packageSack.ListPackageSack(pkgs)
    else:
      # If the search for the package return nothing, search for what
      # provides it because the requirement might be provided by
      # something that doesn't have the same name as the requirement.
      pkgSack = self.whatProvides(name, kwargs.get('flag', 'EQ'), (epoch, ver, rel))
      name_mismatch = True

    pkgs = pkgSack.returnNewestByName()

    # yum version 3.0.1 returns a list of lists in returnNewestByName()
    pkgsflat = []
    for pkg in pkgs:
      if type(pkg) == type([]):
        pkgsflat.extend(pkg)
      else:
        pkgsflat.append(pkg)
    pkgs = pkgsflat

    del pkgSack

    pkgbyname = {}
    for pkg in pkgs:
      pkgbyname.setdefault(pkg.name, []).append(pkg)

    lst = []
    for pkgs in pkgbyname.values():
      lst.extend(self.bestPackagesFromList(pkgs, arch=self.archstr))
    pkgs = lst

    return pkgs, name_mismatch

  def getBestAvailablePackage(self, name=None, ver=None, rel=None, arch=None, epoch=None):
    pkgs, name_mismatch = self.getBestAvailablePackages(
             name = name,
             ver = ver,
             rel = rel,
             arch = arch,
             epoch = epoch
           )
    if pkgs:
      try:
        po = pkgs[0]
        thispkgobsdict = self.up.checkForObsolete([po.pkgtup])
        if self.tsInfo.exists(pkgtup=po.pkgtup):
          po = self.tsInfo.getMembers(pkgtup=po.pkgtup)[0]
        elif thispkgobsdict.has_key(po.pkgtup):
          obsoleting = thispkgobsdict[po.pkgtup][0]
          obsoleting_pkg = self.getPackageObject(obsoleting)
          po = obsoleting_pkg
        return po
      finally:
        if name_mismatch:
          if self.dsCallback: self.dsCallback.foundObsolete((name, epoch, ver, rel, arch), po.pkgtup)
    return None

  def install(self, po=None, name=None, **kwargs):
    if po is None and name is None:
      raise yum.Errors.InstallError("nothing specified to install")
    if not po:
      po = self.getBestAvailablePackage(name=name)
      if po is None:
        raise yum.Errors.InstallError("nothing provides '%s'" % po)
    return yum.YumBase.install(self, po=po)

  def teardown(self):
    self.close()
    self.closeRpmDB()
    self.doUnlock()

    self.repos = None
    self.pkgSack = None
    self.conf = None
    self.rpmdb = None
    self.tsInfo = None
    self.up = None
    self.comps = None
    del self.ts

class Depsolver(SystemStudioYum):
  def __init__(self, config='/etc/yum.conf', root='/tmp/depsolver',
               arch=None, callback=None):

    SystemStudioYum.__init__(self,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = callback
    )

    self.resolved_deps = {}
    self.deps = {}
    self.final_pkgobjs = {}

  def getPackageDeps(self, txmbr, errors):
    return_list = []
    po = txmbr.po
    reqs = po.requires
    provs = po.provides

    txmbrdeps = {}

    # process each requires
    for req in reqs:
      # skip rpmlib and config requires
      if req[0].startswith('rpmlib(') or req[0].startswith('config('):
        continue

      # skip circular requires/provides
      if req in provs:
        continue

      # figure out a package that provides the necessary capability
      dep = self.deps.get(req, None)
      if dep is None:
        dep = self._provideToPkg(req)
        if dep is None:
          errors.append("missing dependency '%s' for '%s'" % \
                          (yum.misc.prco_tuple_to_string(req), txmbr.po))
          continue

      txmbrdeps[req] = dep.pkgtup

      # skip circular requires/provides, again
      if txmbr.name == dep.name:
        continue

      return_list.append(dep)

      if self.tsInfo.exists(dep.pkgtup):
        # provider already exists in transaction info, get it
        pkgs = self.tsInfo.getMembers(pkgtup=dep.pkgtup)
        member = self.bestPackagesFromList(pkgs, arch=self.archstr)[0]
      else:
        # select provider and add it to list of unresolved items
        member = self.tsInfo.addInstall(dep)

      # perform dependency mapping
      found = False
      for dependspo in txmbr.depends_on:
        if member.po == dependspo:
          found = True
          break
      if not found:
        txmbr.setAsDep(member.po)

    self.resolved_deps.setdefault(txmbr.po.pkgtup, {}).update(txmbrdeps)
    return return_list

  def _provideToPkg(self, req):
    "Find a package that provides the capability specified in req"
    best = None
    (r,f,v) = req

    satisfiers = []
    for po in self.whatProvides(r,f,v):
      if self.tsInfo.getMembers(po.pkgtup):
        self.deps[req] = po
        return po
      if po not in satisfiers:
        satisfiers.append(po)

    if satisfiers:
      bestpkgs = self.bestPackagesFromList(satisfiers, arch=self.archstr)
      po = bestpkgs[0]

      thispkgobsdict = self.up.checkForObsolete([po.pkgtup])
      if thispkgobsdict.has_key(po.pkgtup):
        obsoleting = thispkgobsdict[po.pkgtup][0]
        obsoleting_pkg = self.getPackageObject(obsoleting)
        self.deps[req] = obsoleting_pkg
        return obsoleting_pkg
      self.deps[req] = po
      return po
    return None

  def installPackageDeps(self, txmbr, errors):
    deps = self.getPackageDeps(txmbr, errors)
    for dep in deps:
      self.tsInfo.addInstall(dep)
      #print "Added %s for %s" % (dep, txmbr.po)

  def getPackageObjects(self, unresolved=None):
    if ( len(self.tsInfo) == 0 or
         unresolved and len(unresolved) == 0 ):
      raise yum.Errors.MiscError("No packages found to resolved.")
    if self.dsCallback: self.dsCallback.start()
    unresolved = unresolved or self.tsInfo.getMembers()
    errors = []
    while unresolved:
      if self.dsCallback: self.dsCallback.tscheck(unresolved=len(unresolved))
      for txmbr in unresolved:
        # if redhat-lsb is depsolved early on the process, it brings down
        # a bunch of packages that are not required.
        if txmbr.name == 'redhat-lsb' and len(unresolved) > 1:
          continue
        self.final_pkgobjs[txmbr.po] = None
        if self.dsCallback: self.dsCallback.pkgAdded()
        self.installPackageDeps(txmbr, errors)
      unresolved = []
      for txmbr in self.tsInfo:
        if not self.final_pkgobjs.has_key(txmbr.po):
          unresolved.append(txmbr)
      if unresolved and self.dsCallback: self.dsCallback.restartLoop()
    if self.dsCallback: self.dsCallback.end()
    if len(errors) != 0:
      errormsg = "The following errors occurred during dependency resolution:\n"
      for error in errors:
        errormsg = '%s * %s\n' % (errormsg, error)
      raise DepsolveError(errormsg)
    return self.final_pkgobjs.keys()

class DummyRpmDBPackageSack(yum.rpmsack.RPMDBPackageSack):
  def __init__(self, root='/'):
    pass

  def _get_pkglist(self):
    return []
  pkglist = property(_get_pkglist, None)

  def dropCachedData(self):
    pass

  def readOnlyTS(self):
    return None

  def searchAll(self, name, query_type='like'):
    return []

  def searchFiles(self, name):
    return []

  def searchPrco(self, name, prcotype):
    return []

  def installed(self, name=None, arch=None, epoch=None, ver=None, rel=None, po=None):
    return False

  def returnNewestByNameArch(self, naTup=None):
    return None

  def returnNewestByName(self, name=None):
    return None

  def returnPackages(self, repoid=None):
    return []

  def searchPrimaryFieldsMultipleStrings(self, fields, searchstrings,
                                         lowered=False):
    return []

  def searchNevra(self, name=None, epoch=None, ver=None, rel=None, arch=None):
    return []

  def contains(self, name=None, arch=None, epoch=None, ver=None, rel=None, po=None):
    return False

  def getPkgList(self):
    return self.pkglist

  def getHdrList(self):
    return []

  def getNameArchPkgList(self):
    return []

  def getNamePkgList(self):
    return []

  def returnTupleByKeyword(self, name=None, arch=None, epoch=None, ver=None, rel=None):
    return []

  def returnHeaderByTuple(self, pkgtuple):
    return []

  def returnIndexByTuple(self, pkgtuple):
    return []

  def whatProvides(self, name, flags, version):
    return []