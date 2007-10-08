import pickle
import yum

from dims import difftest
from dims import filereader

from dims.depsolver import DepSolver

from dimsbuild.callback import DepsolveCallback
from dimsbuild.event    import Event
from dimsbuild.logging  import L0, L1

API_VERSION = 5.0

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

class PkglistEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pkglist',
      provides = ['pkglist'],
      requires = ['required-packages', 'repos'],
    )

    self.dsdir = self.mddir / '.depsolve'
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
    self.DATA['output'].append(self.pkglistfile)

    self.rddirs = [] # list of repodata dirs across all repos

    for repo in self.cvars['repos'].values():
      self.rddirs.append(repo.ljoin(repo.repodata_path, 'repodata'))

    self.DATA['input'].extend(self.rddirs)

  def run(self):
    self.log(0, L0("resolving package list"))
    self.io.clean_eventcache()

    # copy pkglist
    if self.docopy:
      self.io.sync_input()
      self.log(1, L1("reading supplied package list"))
      if self.dsdir.exists():
        self.dsdir.rm(recursive=True)
      self.diff.write_metadata()
      return

    # create pkglist
    self.log(1, L1("generating new package list"))
    if not self.dsdir.exists(): self.dsdir.mkdirs()

    depsolve_results = {}

    depsolve_file = self.mddir / 'depsolve-results'
    self.DATA['output'].append(depsolve_file)
    if depsolve_file.exists():
      f = open(depsolve_file)
      depsolve_cache = pickle.load(f)
      f.close()
    else:
      depsolve_cache = {}

    removed = []
    added = []
    diffdict = self.diff.handlers['variables'].diffdict
    if diffdict.has_key("cvars['required-packages']"):
      r, a = diffdict["cvars['required-packages']"]
      if not isinstance(r, difftest.NoneEntry) and \
         not isinstance(r, difftest.NewEntry):
        removed.extend([ x for x in r if x not in a])
      if not isinstance(a, difftest.NoneEntry) and \
         not isinstance(a, difftest.NewEntry):
        added.extend([ x for x in a ])
    added.extend([ x for x in self.cvars.get('required-packages', []) \
                   if x not in added ])
    self.__massage_cache(depsolve_cache, added, removed)

    repoconfig = self._create_repoconfig()
    solver = DepSolver(config=str(repoconfig),
                       root=str(self.dsdir),
                       arch=self.arch)
    solver.setup()

    cust_pkgs = [ x[0] for x in self.cvars.get('custom-rpms-info', []) ]
    reqd_pkgs = [ x for x in added if x not in cust_pkgs ]

    callback = DepsolveCallback(self.logger, len(cust_pkgs) + len(reqd_pkgs))
    # in the case of incremental-depsolving, have to add the custom
    # rpms before any of the other rpms. This is because, otherwise,
    # the rpms that are obsoleted by the custom rpms will get brought
    # down depending on when the custom rpm is added to the package
    # sack.
    callback.start()
    for pkg in cust_pkgs:
      callback.pkg_added(pkg)
      try:
        self.__depsolve(pkg, solver, depsolve_cache, depsolve_results)
      except yum.Errors.InstallError:
        pass
    for pkg in reqd_pkgs:
      callback.pkg_added(pkg)
      try:
        self.__depsolve(pkg, solver, depsolve_cache, depsolve_results)
      except yum.Errors.InstallError:
        pass
    callback.finish()
    repoconfig.remove()

    f = open(depsolve_file, 'w')
    pickle.dump(depsolve_results, f)
    f.close()

    pkgtups = [ x.pkgtup for x in solver.tsInfo.getMembers() ]

    self.log(1, L1("verifying package list"))
    # extract pkg names for checking
    nlist = [ n for n,_,_,_,_ in pkgtups ]
    for pcheck in self.cvars.get('user-required-packages', []):
      if pcheck not in nlist:
        raise DepSolveError("User-specified package '%s' not found in resolved pkglist" % pcheck)
    del nlist

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,_,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s' % (n,v,r))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    filereader.write(pkglist, self.pkglistfile)

    self.DATA['output'].append(self.dsdir)
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    if not self.pkglistfile.exists():
      raise RuntimeError("missing package list file: '%s'" % self.pkglistfile)
    self.cvars['pkglist'] = filereader.read(self.pkglistfile)

  def _create_repoconfig(self):
    repoconfig = self.TEMP_DIR / 'depsolve.repo'
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

      conf.extend([
        '[%s]' % repo.id,
        'name = %s' % repo.id,
        'baseurl = file://%s' % repo.ljoin(repo.repodata_path),
        '\n',
      ])
    filereader.write(conf, repoconfig)
    return repoconfig

  def __massage_cache(self, cache, added, removed):
    """
    Remove items in cache that are not needed anymore.
    """
    for rm in removed:
      if cache.has_key(rm):
        #print rm, "is not needed anymore"
        cache.pop(rm)
    topop = []
    for pkg, info in cache.items():
      for dep in info[1]:
        if dep[0] in removed:
          #print dep[0], "is obsolete, removing", pkg
          topop.append(pkg)
          break
    for rm in topop:
      cache.pop(rm)

  def __depsolve(self, package, solver, cache, results):
    """
    Incremental depsolving, but before actually running depsolve,
    check cache.
    """
    txmbrs = solver.install(name=package)
    pkgtup = txmbrs[0].pkgtup
    n,_,_,v,r = pkgtup

    # If the package has been depsolved before, try to skip depsolving
    # again.  If an error is raised while adding the dependencies to
    # the package sack, it means that the dependency has changed or is
    # missing; in this case run depsolve on the package again.
    depsolve = True
    if cache.has_key(n) and cache[n][0] == pkgtup:
      deps = cache[n][1]
      try:
        for dep in deps:
          solver.install(name=dep[0])
      except yum.Errors.InstallError, e:
        depsolve = True
      else:
        depsolve = False
        results[n] = (pkgtup, deps)

    if depsolve:
      deps = solver.resolveDeps()
      results[n] = (pkgtup, deps)


EVENTS = {'software': [PkglistEvent]}

#------ ERRORS ------#
class DepSolveError(StandardError): pass
