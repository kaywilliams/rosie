import copy
import pickle
import re
import yum

from dims import difftest
from dims import pps

from dims.depsolver import DepSolver

from dimsbuild.callback  import BuildDepsolveCallback
from dimsbuild.event     import Event
from dimsbuild.logging   import L1

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
    solver = IDepSolver(depsolve_file,
                        config=str(repoconfig), root=str(self.dsdir),
                        arch=self.arch, callback=BuildDepsolveCallback(self.logger),
                        handler=IDepSolverHandler(todepsolve,
                                                  self.diff.handlers['variables'].diffdict))
    solver.setup()

    for package in todepsolve:
      try:
        solver.install(name=package)
      except yum.Errors.InstallError, e:
        pass
    solver.resolveDeps()

    pkgtups = [ x.pkgtup for x in solver.tsInfo.getMembers() ]

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

  def verify_pkglist_content(self):
    "pkglist contains user required packages"
    pkglist = [ NVR_REGEX.match(x).groups()[0] for x in self.cvars['pkglist'] ]
    missing = []
    for pkg in self.cvars['user-required-packages']:
      if pkg not in pkglist:
        missing.append(pkg)

    self.verifier.failUnless(len(missing) == 0,
      "missing package%s in package list: %s" % \
        (len(missing) != 1 and 's' or '', missing))

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

class IDepSolverHandler(object):
  def __init__(self, todepsolve, variables_diff):
    self.todepsolve = todepsolve
    self.variables_diff = variables_diff
    self.cache_mapping = {}
    self.removed = []

  def update_cache(self, solver):
    """
    Remove items in cache that are not needed anymore.
    """
    new_cache = {}
    cache = solver.depsolve_cache

    diffdict = self.variables_diff
    if diffdict.has_key("cvars['required-packages']"):
      r,a = diffdict["cvars['required-packages']"]
      if not isinstance(r, difftest.NoneEntry) and \
             not isinstance(r, difftest.NewEntry):
        self.removed.extend([ x for x in r if x not in a])

    for pkg in cache:
      self.cache_mapping[pkg[0]] = pkg

    for item in self.todepsolve:
      if self._recursive_check(cache, item, [], solver._provideToPkg):
        self._recursive_add(cache, new_cache, item)

    cache.clear()
    cache.update(new_cache)

  def _recursive_check(self, cache, package, processed, providefunc):
    """
    Check to see whether any package brought down by a required
    package requires a package that is a previously-required
    package. Return False in this case. Also, return False if the
    package we are about to add is older than the one found in
    input repositories.
    """
    if package in self.removed:
      return False
    if self.cache_mapping.has_key(package) and \
           not package in processed:
      processed.append(package)
      best_package = providefunc((package, None, None))
      if best_package is None:
        return False
      if best_package.pkgtup != self.cache_mapping[package]:
        return False
      for dep in cache[self.cache_mapping[package]]:
        if not self._recursive_check(cache, dep[0], processed, providefunc):
          return False
    return True

  def _recursive_add(self, cache, new_cache, package):
    """
    Should be called iff _recursive_check() returns True. The
    _recursive_check() function will return True only if none of the
    package parameter's dependencies are in the list of
    previously-required packages.
    """
    if self.cache_mapping.has_key(package) and \
           not new_cache.has_key(self.cache_mapping[package]):
      new_cache[self.cache_mapping[package]] = cache[self.cache_mapping[package]]
      for dep in new_cache[self.cache_mapping[package]]:
        self._recursive_add(cache, new_cache, dep[0])

class IDepSolver(DepSolver):
  def __init__(self, cache_file, config='/etc/yum.conf',
               root='/tmp/depsolver', arch=None, callback=None, handler=None):
    DepSolver.__init__(self, config=config, root=root,
                       arch=arch, callback=callback)
    self.cache_file = P(cache_file)
    self.depsolve_cache = {}
    self.handler = handler

  def setup(self):
    DepSolver.setup(self)
    if self.cache_file.exists():
      f = self.cache_file.open()
      self.depsolve_cache = pickle.load(f)
      f.close()
    if self.handler:
      self.handler.update_cache(self)

  def resolveDeps(self):
    "Resolve dependencies on all selected packages and groups."
    self.initActionTs()
    if self.dsCallback: self.dsCallback.start()
    unresolved = self.tsInfo.getMembers()
    while len(unresolved) > 0:
      if self.dsCallback: self.dsCallback.tscheck(len(unresolved))
      toremove = []
      for txmbr in unresolved:
        if self.depsolve_cache.has_key(txmbr.pkgtup):
          try:
            self.__recursive_install(txmbr.pkgtup)
          except yum.Errors.InstallError, e:
            #print e
            pass
          else:
            if self.dsCallback: self.dsCallback.pkgAdded(txmbr.pkgtup)
            toremove.append(txmbr)
      for rm in toremove: unresolved.remove(rm)
      unresolved = self.tsCheck(unresolved)
      if self.dsCallback: self.dsCallback.restartLoop()
    self.deps = {}
    f = self.cache_file.open('w')
    pickle.dump(self.depsolve_results, f)
    f.close()

  def __recursive_install(self, pkgtup):
    for dep in self.depsolve_cache.get(pkgtup, []):
      if not self.tsInfo.exists(dep):
        txmbrs = self.install(pkgtup=dep)
        self.__recursive_install(dep)
      self.depsolve_results.setdefault(pkgtup, []).append(dep)


#------ ERRORS ------#
class DepSolveError(StandardError): pass
