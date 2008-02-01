import re
import rpmUtils.arch

from rendition import depsolver
from rendition import difftest

from spin.callback  import BuildDepsolveCallback
from spin.constants import KERNELS
from spin.event     import Event
from spin.logging   import L1

from spin.modules.shared import idepsolver

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

NVRA_REGEX = re.compile('(?P<name>.+)'    # rpm name
                        '-'
                        '(?P<version>.+)' # rpm version
                        '-'
                        '(?P<release>.+)' # rpm release
                        '\.'
                        '(?P<arch>.+)')   # rpm architecture

INCREMENTAL_DEPSOLVE = True

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
      self.io.add_xpath('.', self.mddir, id='pkglist')
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
    # copy pkglist
    if self.docopy:
      self.io.sync_input(cache=True)
      self.log(1, L1("reading supplied package list"))
      if self.dsdir.exists():
        self.dsdir.rm(recursive=True)
      self.diff.write_metadata()
      return

    # create pkglist
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    self._verify_repos()
    repoconfig = self._create_repoconfig()
    required_packages = self.cvars.get('required-packages', [])
    user_required = self.cvars.get('user-required-packages', [])

    if INCREMENTAL_DEPSOLVE:
      old_packages = []
      diffdict = self.diff.handlers['variables'].diffdict
      if diffdict.has_key("cvars['required-packages']"):
        prev, curr = diffdict["cvars['required-packages']"]
        if ( prev is None or
             isinstance(prev, difftest.NewEntry) or
             isinstance(prev, difftest.NoneEntry) ):
          prev = []
        if prev:
          old_packages.extend([ x for x in prev if x not in curr ])

      pkgtups = idepsolver.resolve(all_packages = required_packages,
                                   old_packages = old_packages,
                                   required = user_required,
                                   config = str(repoconfig),
                                   root = str(self.dsdir),
                                   arch = self.arch,
                                   callback = BuildDepsolveCallback(self.logger),
                                   logger = self.logger)
    else:
      self.log(1, L1("generating new package list"))
      pkgtups = depsolver.resolve(packages = required_packages,
                                  required = user_required,
                                  config = str(repoconfig),
                                  root = str(self.dsdir),
                                  arch = self.arch,
                                  callback = BuildDepsolveCallback(self.logger))

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,a,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s.%s' % (n,v,r,a))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    self.pkglistfile.write_lines(pkglist)

    self.DATA['output'].extend([self.dsdir, self.pkglistfile, repoconfig])
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    try:
      self.cvars['pkglist'] = self.pkglistfile.read_lines()
    except:
      pass # handled by verification below

  def verify_pkglistfile_exists(self):
    "pkglist file exists"
    self.verifier.failUnlessExists(self.pkglistfile)

  def verify_kernel_arch(self):
    "kernel arch matches arch in config"
    matched = False
    for pkg in self.cvars['pkglist']:
      n,v,r,a = NVRA_REGEX.match(pkg).groups()
      if n not in KERNELS: continue
      self.verifier.failUnlessEqual(rpmUtils.arch.getBaseArch(a), self.basearch,
        "the base arch of kernel package '%s' does not match the specified "
        "base arch '%s'" % (pkg, self.basearch))
      matched = True

    self.verifier.failUnless(matched, "no kernel package found")

  def _verify_repos(self):
    for repo in self.cvars['repos'].values():
      # determine if repodata folder changed
      rddir_changed = False
      for rddir in self.rddirs:
        for file in self.diff.handlers['input'].diffdict.keys():
          if file.startswith(rddir):
            rddir_changed = True; break
        if rddir_changed: break
      if rddir_changed:
        (self.dsdir/repo.id).rm(recursive=True, force=True)

  def _create_repoconfig(self):
    repoconfig = self.mddir / 'depsolve.repo'
    if repoconfig.exists():
      repoconfig.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    for repo in self.cvars['repos'].values():
      conf.extend(str(repo).splitlines())
    repoconfig.write_lines(conf)
    return repoconfig
