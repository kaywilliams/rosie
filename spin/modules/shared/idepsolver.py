import cPickle
import yum

from rendition import pps

from rendition.depsolver import Depsolver

def resolve(packages=None, required=None, remove=None, pkglist=None,
            config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
            callback=None):
  solver = IDepsolver(
             packages = packages,
             required = required,
             remove = remove,
             pkglist = pkglist,
             config = config,
             root = root,
             arch = arch,
             callback = callback
           )
  solver.setup()
  pos = solver.getPackageObjects()
  pkgtups = [ po.pkgtup for po in pos ]
  solver.teardown()
  return pkgtups

class IDepsolver(Depsolver):
  def __init__(self, packages=None, required=None, remove=None, pkglist=None,
               config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
               callback=None):
    Depsolver.__init__(self,
      config = str(config),
      root = str(root),
      arch = arch,
      callback = callback
    )
    self.install_packages = packages
    self.pkglist = pps.Path(pkglist)
    self.required = required
    self.remove_packages = remove

    self.installed_packages = {}

    self.cached_file = pps.Path(root) / 'cache'
    self.cached_items = {}

  def setup(self, force=False):
    Depsolver.setup(self)

    if self.cached_file.exists():
      f = self.cached_file.open('r')
      self.cached_items = cPickle.load(f)
      f.close()
      for pkgtup, deps in self.cached_items.items():
        for tup in [pkgtup] + deps:
          if self.installed_packages.has_key(tup):
            continue
          try:
            self.installed_packages[tup] = self.getPackageObject(tup)
          except yum.Errors.DepError:
            self.removePackages(pkgtup=pkgtup)

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
    else:
      pkgSack = self.whatProvides(name, 'EQ', (epoch, ver, rel))

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

  def getDeps(self, pkgtup):
    processed = {}
    rtn = set()
    pkgtups = [pkgtup]
    while pkgtups:
      pkgtup = pkgtups.pop()
      processed[pkgtup] = None
      rtn.add(pkgtup)
      if self.cached_items.has_key(pkgtup):
        for x in self.cached_items[pkgtup]:
          if not processed.has_key(x):
            pkgtups.append(x)
    return list(rtn)

  def whatRequires(self, po=None, pkgtup=None):
    if pkgtup is None:
      pkgtup = po.pkgtup
    rtnlist = set()
    for tup, deps in self.cached_items.items():
      if pkgtup in deps:
        rtnlist.add(tup)
    return list(rtnlist)

  def removePackages(self, po=None, pkgtup=None):
    if pkgtup is None:
      pkgtups = self.getDeps(po.pkgtup)
    else:
      pkgtups = self.getDeps(pkgtup)

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
    for pkg in self.remove_packages:
      po = self.getInstalledPackage(name=pkg)
      if po is not None:
        self.removePackages(po=po)

    # handle new packages
    for package in self.install_packages:
      instpo = self.getInstalledPackage(name=package)
      bestpo = self.getBestAvailablePackage(name=package)
      if instpo is None:
        if bestpo is None and package in self.required:
          raise yum.Errors.InstallError("No packages provide '%s'" % package)
        elif bestpo is not None:
          self.installPackage(po=bestpo)

    # handle packages to be removed, updated
    deps = [ (pkgtup, po) for pkgtup, po in self.installed_packages.items() ]
    for pkgtup, po in deps:
      what_requires = self.whatRequires(pkgtup=pkgtup)
      required = False
      if len(what_requires) > 1 or \
         len(what_requires) == 1 and what_requires[0] != pkgtup or \
         pkgtup[0] in self.install_packages:
        required = True
      for prov in po.provides:
        # if a package provides something that's required, don't remove
        if prov[0] in self.install_packages:
          required = True
          break
      if not required:
        self.removePackages(pkgtup=pkgtup)
        continue
      bestpo = self.getBestAvailablePackage(name=pkgtup[0])
      if po is None:
        self.removePackages(pkgtup=pkgtup)
      if bestpo is not None and po is not None and bestpo != po:
        self.removePackages(po=po)
        self.installPackage(po=bestpo)

    for po in self.installed_packages.values():
      self.install(po=po)

    pos = Depsolver.getPackageObjects(self)

    f = self.cached_file.open('w')
    cPickle.dump(self.resolved_deps, f)
    f.close()

    return pos
