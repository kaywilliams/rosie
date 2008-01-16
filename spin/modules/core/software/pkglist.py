import yum

from rendition import difftest

from spin.callback import BuildDepsolveCallback
from spin.event    import Event
from spin.logging  import L1

from spin.modules.shared.idepsolve import IDepsolver

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
        toremove.extend([ x for x in prev if x not in curr ])

    solver = IDepsolver(
               repoconfig,
               self.dsdir,
               self.arch,
               BuildDepsolveCallback(self.logger),
               self.pkglistfile,
               user_required,
               required_packages,
               toremove
             )
    solver.setup()
    solver.getPackageObjects()

    pkgtups = [ x.pkgtup for x in solver.polist ]

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,a,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s.%s' % (n,v,r,a))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    self.pkglistfile.write_lines(pkglist)

    self.DATA['output'].extend([self.dsdir, self.pkglistfile, repoconfig])
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
