import cPickle as pickle
import copy
import re
import yum

from dims import difftest
from dims import pps

from dims.depsolver import DepSolver

from dimsbuild.callback import BuildDepsolveCallback
from dimsbuild.event    import Event
from dimsbuild.logging  import L1

P = pps.Path

API_VERSION = 5.0
EVENTS = {'software': ['PkglistEvent']}

YUMCONF_HEADER = [
  '[main]',
  'cachedir=',
  'logfile=/depsolve.log',
  'debuglevel=0',
  'errorlevel=0',
  'gpgcheck=0',
  'tolerant=1',
  'exactarch=1',
  'reposdir=/'
  '\n',
]

NVR_REGEX = re.compile('(.+)-([^-]+)-([^-]+)')

class PkglistEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pkglist',
      provides = ['pkglist'],
      requires = ['required-packages', 'repos', 'user-required-packages'],
    )

    self.dsdir = self.mddir / 'depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'required-packages\']'],
      'input':     [],
      'output':    [],
    }
    self.docopy = self.config.pathexists('text()')

  def setup(self):
    self.diff.setup(self.DATA)

    # setup if copying pkglist
    if self.docopy:
      self.io.setup_sync(self.mddir, id='pkglist', xpaths=['.'])
      self.pkglistfile = self.io.list_output(what='pkglist')[0]
      return

    # setup if creating pkglist
    self.pkglistfile = self.mddir / 'pkglist'

    self.rddirs = [] # list of repodata dirs across all repos

    for repo in self.cvars['repos'].values():
      self.rddirs.append(repo.localurl/'repodata')

    self.DATA['input'].extend(self.rddirs)

  def run(self):
    self.io.clean_eventcache()

    # copy pkglist
    if self.docopy:
      self.io.sync_input(cache=True)
      self.log(1, L1("reading supplied package list"))
      if self.dsdir.exists():
        self.dsdir.rm(recursive=True)
      self.diff.write_metadata()
      return

    # create pkglist
    self.log(1, L1("generating new package list"))
    if not self.dsdir.exists(): self.dsdir.mkdirs()

    repoconfig = self._create_repoconfig()
    depsolve_file = self.mddir / 'depsolve-results'
    todepsolve = copy.deepcopy(self.cvars.get('required-packages', []))
    user_required = copy.deepcopy(self.cvars.get('user-required-packages', []))
    removed_items = []
    diffdict = self.diff.handlers['variables'].diffdict
    if diffdict.has_key("cvars['required-packages']"):
      prev, curr = diffdict["cvars['required-packages']"]
      if ( prev is not None and
           not isinstance(prev, difftest.NoneEntry) and
           not isinstance(prev, difftest.NewEntry) ):
        removed_items.extend([ x for x in prev if x not in curr ])

    solver = IDepSolver(depsolve_file, todepsolve, removed_items, user_required,
                        config=str(repoconfig), root=str(self.dsdir),
                        arch=self.arch, callback=BuildDepsolveCallback(self.logger))
    solver.setup()
    solver.resolveDeps()
    pkgtups = [ x.pkgtup for x in solver.tsInfo.getMembers() ]
    solver.teardown()

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,_,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s' % (n,v,r))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    self.pkglistfile.write_lines(pkglist)

    self.DATA['output'].extend([self.dsdir, self.pkglistfile, depsolve_file,
                                repoconfig])
    self.diff.write_metadata()
    solver = None

  def apply(self):
    self.io.clean_eventcache()
    try:
      self.cvars['pkglist'] = self.pkglistfile.read_lines()
    except:
      pass # handled by verification below

  def verify_pkglistfile_exists(self):
    "pkglist file exists"
    self.verifier.failUnless(self.pkglistfile.exists(),
      "missing package list file '%s'" % self.pkglistfile)

  def _create_repoconfig(self):
    repoconfig = self.mddir / 'depsolve.repo'
    if repoconfig.exists():
      repoconfig.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    for repo in self.cvars['repos'].values():
      # determine if repodata folder changed
      rddir_changed = False
      for rddir in self.rddirs:
        for file in self.diff.handlers['input'].diffdict.keys():
          if file.startswith(rddir):
            rddir_changed = True
            break

      if rddir_changed:
        ## HACK: delete a folder's depsolve metadata if it has changed.
        (self.dsdir/repo.id).rm(recursive=True, force=True)

      conf.extend(str(repo).split('\n'))
    repoconfig.write_lines(conf)
    return repoconfig


class IDepSolver(DepSolver):
  def __init__(self, cache_file, todepsolve, removed_items, user_required,
               config='/etc/yum.conf', root='/tmp/depsolver', arch=None, callback=None):
    DepSolver.__init__(self, config=config, root=root,
                       arch=arch, callback=callback)
    self.cache_file = P(cache_file)
    self.depsolve_results = {}
    self.depsolve_cache = {}
    self.removed_items = removed_items
    self.user_required = user_required
    self.todepsolve = todepsolve
    self.unresolved = set()

  def setup(self):
    DepSolver.setup(self)
    if self.cache_file.exists():
      f = self.cache_file.open()
      self.depsolve_cache = pickle.load(f)
      f.close()
    self.filterCache()
    for package in self.todepsolve:
      try:
        txmbrs = self.install(name=package)
        for po in txmbrs:
          self.unresolved.add((po, package))
          self.depsolve_results.setdefault(package, set()).add(po.pkgtup)
      except yum.Errors.InstallError, e:
        if package in self.user_required:
          raise DepSolveError("User required package '%s' not found" % package)

  def resolveDeps(self):
    "Resolve dependencies on all selected packages and groups."
    self.initActionTs()
    if self.dsCallback: self.dsCallback.start()
    unresolved = self.unresolved
    while len(unresolved) > 0:
      if self.dsCallback:
        self.dsCallback.tscheck(len(unresolved))
      self.installFromCache(unresolved)
      unresolved = self.tsCheck(unresolved)
      if self.dsCallback:
        self.dsCallback.restartLoop()
    self.deps = {}
    f = self.cache_file.open('w')
    pickle.dump(self.depsolve_results, f)
    f.close()

  def tsCheck(self, tocheck):
    "Attempt to resolve dependencies on items in tocheck."
    unresolved = set()
    for txmbr, pkgname in tocheck:
      self.depsolve_results[txmbr.name] = set()

      # some kind of speed optimization
      if txmbr.name == 'redhat-lsb' and len(tocheck) > 2:
        unresolved.add((txmbr, pkgname))
        continue

      if self.dsCallback:
        self.dsCallback.pkgAdded(txmbr.po.pkgtup)

      if txmbr.output_state not in yum.constants.TS_INSTALL_STATES:
        continue

      # get requires and provides for transaction member
      reqs = txmbr.po.returnPrco('requires')
      provs = txmbr.po.returnPrco('provides')

      # process each requires
      for req in reqs:
        # skip rpmlib and config requires
        if req[0].startswith('rpmlib(') or req[0].startswith('config('):
          continue

        # skip circular requires/provides
        if req in provs:
          continue

        # figure out a package that provides the necessary capability
        dep = self.findBestPackageByNfv(req)
        if dep is None:
          #raise DepSolveError("Unresolvable dependency %s for package %s"
          #                    % (str(req), txmbr.name))
          continue

        self.depsolve_results[txmbr.name].add(dep.pkgtup)
        self.depsolve_results.setdefault(pkgname, set()).add(dep.pkgtup)

        # skip circular requires/provides, again
        if txmbr.name == dep.name:
          continue

        if self.tsInfo.exists(dep.pkgtup):
          # provider already exists in transaction info, get it
          pkgs = self.tsInfo.getMembers(pkgtup=dep.pkgtup)
          member = self.bestPackagesFromList(pkgs, arch=self.arch)[0]
          self.depsolve_results.setdefault(pkgname, set()).update(
            self.depsolve_results.get(dep.name, set())
          )
        else:
          # select provider and add it to list of unresolved items
          member = self.tsInfo.addInstall(dep)
          unresolved.add((member, pkgname))

        # perform dependency mapping
        found = False
        for dependspo in txmbr.depends_on:
          if member.po == dependspo:
            found = True; break
        if not found:
          txmbr.setAsDep(member.po)

    # return list of new, unresolved packages
    return unresolved

  def teardown(self):
    DepSolver.teardown(self)
    self.depsolve_results = None
    self.depsolve_cache = None
    self.unresolved = None

  def installFromCache(self, unresolved):
    installed = []
    for txmbr, pkgname in unresolved:
      if self.depsolve_cache.has_key(pkgname):
        for pkgtup in self.depsolve_cache[pkgname]:
          self.install(pkgtup=pkgtup)
          self.depsolve_results.setdefault(pkgname, set()).add(pkgtup)
        if self.dsCallback:
          self.dsCallback.pkgAdded(txmbr.pkgtup)
        installed.append((txmbr, pkgname))
    for item in installed:
      unresolved.remove(item)

  def filterCache(self):
    """
    Remove items in cache that are not needed anymore.
    """
    for package in self.removed_items:
      if self.depsolve_cache.has_key(package):
        self.depsolve_cache.pop(package)

    stale_data = set()
    for package, deps in self.depsolve_cache.items():
      for dep in deps:
        best_package = self.findBestPackageByName(dep[0])
        if best_package is None or \
            best_package.pkgtup != dep:
          stale_data.add(package)

    for item in stale_data:
      self.depsolve_cache.pop(item)

#------ ERRORS ------#
class DepSolveError(Exception): pass
