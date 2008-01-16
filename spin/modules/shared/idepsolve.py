import re
import yum

from rendition import pps
from rendition import xmllib

from rendition.depsolver import Depsolver

NVRA_REGEX = re.compile('(?P<name>.+)'    # rpm name
                        '-'
                        '(?P<version>.+)' # rpm version
                        '-'
                        '(?P<release>.+)' # rpm release
                        '\.'
                        '(?P<arch>.+)')   # rpm architecture

class IDepsolver(Depsolver):
  def __init__(self, config, root, arch, callback,
               pkglist, user_reqs, install_packages, remove_packages):
    Depsolver.__init__(self,
      install_packages = install_packages,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = callback
    )
    self.pkglist = pps.Path(pkglist)
    self.user_reqs = user_reqs
    self.remove_packages = remove_packages
    self.installed_packages = {}

    self.cached_file = root / 'cache'
    self.cached_items = {}

  def setup(self, force=False):
    Depsolver.setup(self)

    if self.cached_file.exists():
      tree = xmllib.config.read(self.cached_file)
      self.cached_items = xmllib.serialize.unserialize(tree)
      toremove = set()
      for pkgtup, deps in self.cached_items.items():
        for tup in [pkgtup] + deps:
          if self.installed_packages.has_key(tup):
            continue
          try:
            self.installed_packages[tup] = self.getPackageObject(tup)
          except yum.Errors.DepError:
            toremove.add(pkgtup)
      self.removePackages(pkgtups=list(toremove))

  def getInstalledPackage(self, name=None, ver=None, rel=None, arch=None, epoch=None):
    for pkgtup_i in self.installed_packages:
      n_i, a_i, e_i, v_i, r_i = pkgtup_i
      pkgtup_o = (name or n_i, arch or a_i, epoch or e_i, ver or v_i, rel or r_i)
      if pkgtup_o == pkgtup_i:
        return self.installed_packages[pkgtup_i]
    return None

  def getBestAvailablePackage(self, name=None, ver=None, rel=None, arch=None, epoch=None):
    pkgs = self.pkgSack.searchNevra(name=name, ver=ver, rel=rel,
                                    arch=arch, epoch=epoch)
    if pkgs:
      pkgSack = yum.packageSack.ListPackageSack(pkgs)
      pkgs = pkgSack.returnNewestByName()
      del pkgSack

      pkgbyname = {}
      for pkg in pkgs:
        pkgbyname.setdefault(pkg.name, []).append(pkg)

      lst = []
      for pkgs in pkgbyname.values():
        lst.extend(self.bestPackagesFromList(pkgs))
      pkgs = lst

    if pkgs:
      po = pkgs[0]
      if self.tsInfo.exists(pkgtup=po.pkgtup):
        return self.tsInfo.getMembers(pkgtup=po.pkgtup)[0]
      thispkgobsdict = self.up.checkForObsolete([po.pkgtup])
      if thispkgobsdict.has_key(po.pkgtup):
        obsoleting = thispkgobsdict[po.pkgtup][0]
        obsoleting_pkg = self.getPackageObject(obsoleting)
        return obsoleting_pkg
      return po
    return None

  def getDeps(self, pos=None, pkgtups=None):
    processed = {}
    if pos is not None:
      pkgtups = [ po.pkgtup for po in pos if po is not None ]
    rtn = set()
    while pkgtups:
      pkgtup = pkgtups.pop()
      processed[pkgtup] = None
      rtn.add(pkgtup)
      if self.cached_items.has_key(pkgtup):
        for x in self.cached_items[pkgtup]:
          if not processed.has_key(x):
            pkgtups.append(x)
    return list(rtn)

  def whatRequires(self, pos=None, pkgtups=None):
    if pkgtups is None:
      pkgtups = [ po.pkgtup for po in pos if po is not None ]
    rtnlist = set()
    for pkgtup, deps in self.cached_items.items():
      for x in pkgtups:
        if x in deps:
          rtnlist.add(x)
    return list(rtnlist)

  def removePackages(self, pos=None, pkgtups=None):
    if pkgtups is None:
      pkgtups = self.getDeps(pos=pos)
    else:
      pkgtups = self.getDeps(pkgtups=pkgtups)

    for pkgtup in pkgtups:
      if self.installed_packages.has_key(pkgtup):
        self.installed_packages.pop(pkgtup)
      if self.cached_items.has_key(pkgtup):
        self.cached_items.pop(pkgtup)

  def installPackage(self, name=None, po=None):
    if name is None and po is None:
      raise yum.Errors.InstallError("nothing specified to install")
    po = po or self.getBestAvailablePackage(name=name)
    self.installed_packages[po.pkgtup] = po

  def getPackageObjects(self):
    # handle obsolete packages
    pos = []
    for pkg in self.remove_packages:
      po = self.getInstalledPackage(name=pkg)
      if po is not None:
        pos.append(po)
    self.removePackages(pos=pos)

    # handle new packages
    for package in self.install_packages:
      instpo = self.getInstalledPackage(name=package)
      bestpo = self.getBestAvailablePackage(name=package)
      if instpo is None:
        if bestpo is None and package in self.user_reqs:
          raise yum.Errors.InstallError("No package to install %s" % package)
        elif bestpo is not None:
          self.installPackage(po=bestpo)

    # handle packages to be removed, updated
    deps = [ (pkgtup, po) for pkgtup, po in self.installed_packages.items() ]
    for pkgtup, po in deps:
      what_requires = self.whatRequires(pkgtups=[pkgtup])
      if ( (len(what_requires) == 0 or
            (len(what_requires) == 1 and what_requires[0] == pkgtup)) and
           pkgtup[0] not in self.install_packages ):
        self.removePackages(pkgtups=[pkgtup])
        continue

      bestpo = self.getBestAvailablePackage(name=pkgtup[0])
      if po is None:
        self.removePackages(pkgtups=[pkgtup])
      if bestpo is not None and po is not None and bestpo != po:
        self.removePackages(pos=[po])
        self.installPackage(po=bestpo)

    for po in self.installed_packages.values():
      self.install(po=po)

    self.resolveDeps()
    xmllib.serialize.serialize(self.resolved_deps).write(self.cached_file)
