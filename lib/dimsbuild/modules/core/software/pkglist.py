import pickle
import re
import yum

from dims import difftest
from dims import filereader
from dims import pps

from dims.depsolver import DepSolver

from dimsbuild.callback  import BuildDepsolveCallback
from dimsbuild.constants import RPM_PNVRA
from dimsbuild.event     import Event
from dimsbuild.logging   import L0, L1

P = pps.Path

API_VERSION = 5.0

RPM_PNVRA_REGEX = re.compile(RPM_PNVRA)

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
      conditionally_requires = ['custom-rpms']
    )

    self.dsdir = self.mddir / '.depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'required-packages\']',
                    'cvars[\'custom-rpms\']'],
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

    repoconfig = self._create_repoconfig()
    depsolve_file = self.mddir / '.depsolve-results'
    self.DATA['output'].append(depsolve_file)
    solver = IDepSolver(depsolve_file,
                        config=str(repoconfig), root=str(self.dsdir),
                        arch=self.arch, callback=BuildDepsolveCallback(self.logger))
    solver.setup()

    self.__update_cache(solver.depsolve_cache)

    todepsolve = self.cvars.get('required-packages', [])

    for package in todepsolve:
      try:
        solver.install(name=package)
      except yum.Errors.InstallError:
        pass
    solver.resolveDeps()
    repoconfig.remove()

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

  def __update_cache(self, cache):
    """
    Remove items in cache that are not needed anymore.
    """
    removed = []
    diffdict = self.diff.handlers['variables'].diffdict
    if diffdict.has_key("cvars['required-packages']"):
      r,a = diffdict["cvars['required-packages']"]
      if not isinstance(r, difftest.NoneEntry) and \
         not isinstance(r, difftest.NewEntry):
        removed.extend([ x for x in r if x not in a])
    if diffdict.has_key("cvars['custom-rpms']"):
      o,n = diffdict["cvars['custom-rpms']"]
      if not isinstance(o, difftest.NewEntry) and \
         not isinstance(o, difftest.NoneEntry) and \
         not isinstance(n, difftest.NewEntry) and \
         not isinstance(n, difftest.NoneEntry):
        for rm in [ x for x in o if x not in n ]:
          removed.append(RPM_PNVRA_REGEX.match(rm).groups()[1])
    for rm in removed:
      if cache.has_key(rm):
        #print rm, "is not needed anymore"
        cache.pop(rm)
    topop = []
    for pkg, deps in cache.items():
      for dep in deps:
        if dep[0] in removed:
          #print dep[0], "is obsolete, removing", pkg
          topop.append(pkg)
          break
    for rm in topop:
      cache.pop(rm)


class IDepSolver(DepSolver):
  def __init__(self, cache_file, config='/etc/yum.conf',
               root='/tmp/depsolver', arch=None, callback=None):
    DepSolver.__init__(self, config=config, root=root,
                       arch=arch, callback=callback)
    self.cache_file = P(cache_file)
    self.depsolve_cache = {}

  def setup(self):
    DepSolver.setup(self)
    if self.cache_file.exists():
      f = open(self.cache_file)
      self.depsolve_cache = pickle.load(f)
      f.close()

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
    f = open(self.cache_file, 'w')
    pickle.dump(self.depsolve_results, f)
    f.close()

  def __recursive_install(self, pkgtup):
    for dep in self.depsolve_cache.get(pkgtup, []):
      if not self.tsInfo.exists(dep):
        self.install(pkgtup=dep)
        self.__recursive_install(dep)
      self.depsolve_results.setdefault(pkgtup, []).append(dep)

EVENTS = {'software': [PkglistEvent]}

#------ ERRORS ------#
class DepSolveError(StandardError): pass
