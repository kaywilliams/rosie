import cPickle
import yum

from rendition import pps

from rendition.depsolver import Depsolver

from spin.callback import IDepsolverCallback
from spin.logging  import L1

def resolve(packages=None, required=None, remove=None, pkglist=None,
            config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
            callback=None, logger=None):
  solver = IDepsolver(
             packages = packages,
             required = required,
             remove = remove,
             pkglist = pkglist,
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
  def __init__(self, packages=None, required=None, remove=None, pkglist=None,
               config='/etc/yum.conf', root='/tmp/depsolver', arch='i686',
               callback=None, logger=None):
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
    self.new_packages = {}

    self.cached_file = pps.Path(root) / 'cache'
    self.cached_items = {}

    self.logger = logger

  def setup(self, force=False):
    Depsolver.setup(self)

    if self.cached_file.exists():
      self.logger.log(3, L1("reading cached data"))
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
            self.remove_packages.append(pkgtup[0])

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
    self.iremove()
    self.iinstall()
    self.iupdate()

    self.logger.log(1, L1("generating new package list"))

    for po in self.installed_packages.values():
      self.install(po=po)

    # build a list of TransctionMember objects that need to have their
    # dependencies resolved.
    unresolved = []
    for txmbr in self.tsInfo.getMembers():
      resolved = True
      if self.cached_items.has_key(txmbr.po.pkgtup):
        for dep in self.cached_items[txmbr.po.pkgtup]:
          if not self.tsInfo.exists(pkgtup=dep):
            resolved = False
            break
      else:
        resolved = False

      if not resolved:
        unresolved.append(txmbr)
      else:
        # if dependencies are resolved, add to Depsolver.final_pkgobjs
        # and add entry in Depsolver.resolved_deps, so that the data is
        # cached for the next time
        try:
          self.resolved_deps[txmbr.po.pkgtup] = self.cached_items[txmbr.po.pkgtup]
        except KeyError:
          # should never happen, but you never know :(. If exception is raised
          # don't mark package as resolved
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
    if not self.remove_packages: return

    if self.logger: remcb = IDepsolverCallback(self.logger)
    else:           remcb = None

    if remcb: remcb.start("removing packages", len(self.remove_packages))
    for pkg in self.remove_packages:
      if remcb: remcb.increment(pkg)
      po = self.getInstalledPackage(name=pkg)
      if po is not None:
        self.removePackages(po=po)
    if remcb: remcb.end()

  def iinstall(self):
    # handle new packages
    if not self.install_packages: return

    if self.logger: inscb = IDepsolverCallback(self.logger)
    else:           inscb = None

    if inscb: inscb.start("checking packages to install", len(self.install_packages))
    for package in self.install_packages:
      if inscb: inscb.increment(package)
      instpo = self.getInstalledPackage(name=package)
      bestpo = self.getBestAvailablePackage(name=package)
      if instpo is None:
        if bestpo is None and package in self.required:
          raise yum.Errors.InstallError("No packages provide '%s'" % package)
        elif bestpo is not None:
          self.installPackage(po=bestpo)
          self.new_packages[bestpo] = None
    if inscb: inscb.end()

  def iupdate(self):
    deps = [ (pkgtup, po)
             for pkgtup, po in self.installed_packages.items()
             if not self.new_packages.has_key(po) ]
    if not deps: return

    if self.logger: updcb = IDepsolverCallback(self.logger)
    else:           updcb = None

    if updcb: updcb.start("checking packages to update", len(deps))
    for pkgtup, po in deps:
      if updcb: updcb.increment(pkgtup[0])
      what_requires = self.whatRequires(pkgtup=pkgtup)
      required = False
      if ( len(what_requires) > 1 or
           len(what_requires) == 1 and what_requires[0] != pkgtup or
           pkgtup[0] in self.install_packages ):
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
    if updcb: updcb.end()
