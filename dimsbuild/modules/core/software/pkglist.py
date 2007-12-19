import cPickle as pickle
import copy
import re
import sys #!
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
    self.DATA['variables'].append('rddirs')

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
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    repos_modified = self._repos_modified()
    repoconfig = self._create_repoconfig()
    required_packages = self.cvars.get('required-packages', [])
    user_required = self.cvars.get('user-required-packages', [])

    toremove = []
    diffdict = self.diff.handlers['variables'].diffdict
    if diffdict.has_key("cvars['required-packages']"):
      prev, curr = diffdict["cvars['required-packages']"]
      if prev is None or \
           isinstance(prev, difftest.NewEntry) or \
           isinstance(prev, difftest.NoneEntry):
        prev = []
      if curr is None or \
           isinstance(curr, difftest.NewEntry) or \
           isinstance(curr, difftest.NoneEntry):
        curr = []
      if prev:
        toremove.extend([ (x, None, None) for x in prev if x not in curr ])

    depsolve_results = self.mddir / 'depsolve-results'
    solver = IDepsolver(repoconfig, self.dsdir, self.arch, depsolve_results,
                        required_packages, user_required, toremove,
                        BuildDepsolveCallback(self.logger))
    solver.setup(diffdict.has_key('rddirs'))
    solver.resolveDeps()
    solver.runTransaction()

    pkgtups = [ x.pkgtup for x in \
                solver.tsInfo.getMembers(None, yum.constants.TS_INSTALL_STATES) ]

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,_,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s' % (n,v,r))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    self.pkglistfile.write_lines(pkglist)

    self.DATA['output'].extend([self.dsdir, self.pkglistfile,
                                repoconfig, depsolve_results])
    self.diff.write_metadata()
    solver.teardown()

    solver.teardown() # stop memory leak

  def apply(self):
    self.io.clean_eventcache()
    try:
      self.cvars['pkglist'] = self.pkglistfile.read_lines()
    except:
      pass # handled by verification below

  def verify_pkglistfile_exists(self):
    "pkglist file exists"
    self.verifier.failUnlessExists(self.pkglistfile)

  def _repos_modified(self):
    changed = False
    for repo in self.cvars['repos'].values():
      # determine if repodata folder changed
      rddir_changed = False
      for rddir in self.rddirs:
        for file in self.diff.handlers['input'].diffdict.keys():
          if file.startswith(rddir):
            rddir_changed = True
            break
        if rddir_changed:
          break
      if rddir_changed:
        ## HACK: delete a folder's depsolve metadata if it has changed.
        (self.dsdir/repo.id).rm(recursive=True, force=True)
        changed = True
    return changed

  def _create_repoconfig(self):
    repoconfig = self.mddir / 'depsolve.repo'
    if repoconfig.exists():
      repoconfig.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    for repo in self.cvars['repos'].values():
      conf.extend(str(repo).split('\n'))
    repoconfig.write_lines(conf)
    return repoconfig

class IDepsolver(DepSolver):
  def __init__(self, config, root, arch, depsolve_results,
               reqpkgs, userreqs, toremove, callback):
    DepSolver.__init__(self, config=str(config), root=str(root),
                       arch=arch, callback=callback)
    self.depsolve_results = depsolve_results
    self.reqpkgs = reqpkgs
    self.userreqs = userreqs
    self.toremove = toremove

  def setup(self, force=False):
    """
    Set up the dependency-solving process.

    @param required_packages : list of required packages
    @param user_required     : list of packages that absolutely need to be
                               there in the resolved transaction set.
    @param toremove          : list of packages that should not be there in the
                               transaction set
    @param force             : do not populate the depsolve process
    """
    DepSolver.setup(self)
    if not self.toremove and not force:
      self.populateRpmDB()

    for n,v,r in self.toremove:
      self.remove(name=n, version=v, release=r)
    for name in self.reqpkgs:
      try:
        self.install(name=name)
      except yum.Errors.InstallError, e:
        if name in self.userreqs:
          raise
        else:
          pass
    updates_available = self.update() # update everything
    if updates_available:
      self.resetRpmDB()

  def populateRpmDB(self):
    if self.depsolve_results.exists():
      for n,a,e,v,r in pickle.load(self.depsolve_results.open('r')):
        for po in self.pkgSack.searchNevra(name=n, arch=a, epoch=e, ver=v, rel=r):
          self.rpmdb.addPackage(po)

  def runTransaction(self):
    DepSolver.runTransaction(self)
    for po in self.rpmdb.returnPackages():
      if not self.tsInfo.exists(pkgtup=po.pkgtup):
        self.tsInfo.addInstall(po)
    f = open(self.depsolve_results, 'w')
    pickle.dump([ x.pkgtup for x in \
                  self.tsInfo.getMembers(None, yum.constants.TS_INSTALL_STATES)
                ], f)
    f.close()
