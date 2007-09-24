from dims import depsolver
from dims import filereader

from dimsbuild.callback import BuildDepsolveCallback
from dimsbuild.event    import Event, RepoMixin #!
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

class PkglistEvent(Event, RepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'pkglist',
      provides = ['pkglist'],
      requires = ['required-packages', 'repos'],
      conditionally_requires = ['user-required-packages'],
    )
    
    self.dsdir = self.mddir / '.depsolve'
    self.pkglistfile = self.mddir / 'pkglist'
    
    self.DATA = {
      'config':    ['/distro/pkglist'],
      'variables': ['cvars[\'required-packages\']'],
      'input':     [],
      'output':    [], 
    }
    self.docopy = self.config.pathexists('/distro/pkglist/text()')
  
  def validate(self):
    self.validator.validate('/distro/pkglist', schemafile='pkglist.rng')
  
  def setup(self):
    self.diff.setup(self.DATA)
    
    # setup if copying pkglist
    if self.docopy:
      self.io.setup_sync(self.mddir, id='pkglist', xpaths=['/distro/pkglist'])
      self.pkglistfile = self.io.list_output(what='pkglist')[0]
      return

    # setup if creating pkglist
    self.pkglistfile = self.mddir / 'pkglist'
    self.DATA['output'].append(self.pkglistfile)
    
    self.rddirs = [] # list of repodata dirs across all repos
    
    for repo in self.getAllRepos():
      self.rddirs.append(repo.ljoin(repo.repodata_path, 'repodata'))
    
    self.DATA['input'].extend(self.rddirs)
  
  def run(self):
    self.log(0, L0("resolving pkglist"))
    self.io.remove_output(all=True)
    
    # copy pkglist    
    if self.docopy:
      self.io.sync_input()
      self.log(1, L1("reading supplied pkglist file"))
      if self.dsdir.exists():
        self.dsdir.rm(recursive=True)
      self.diff.write_metadata()
      return
    
    # create pkglist
    self.log(1, L1("generating new pkglist"))
    if not self.dsdir.exists(): self.dsdir.mkdirs()
      
    repoconfig = self._create_repoconfig()
    pkgtups = depsolver.resolve(
      packages = (self.cvars['required-packages'] or []) + \
                 (self.cvars['user-required-packages'] or []),
      root = str(self.dsdir), # yum is much happier if these are strings
      config = str(repoconfig), # this too
      arch = self.arch,
      callback = BuildDepsolveCallback(self.logger)
    )
    repoconfig.remove()
      
    # verify that final package list contains all user-specified packages
    self.log(1, L1("verifying package list"))
    nlist = [ n for n,_,_,_,_ in pkgtups ] # extract pkg names for checking
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
    if not self.pkglistfile.exists():
      raise RuntimeError("missing package list file: '%s'" % self.pkglistfile)
    self.cvars['pkglist'] = filereader.read(self.pkglistfile)
  
  def _create_repoconfig(self):
    repoconfig = self.TEMP_DIR / 'depsolve.repo'
    if repoconfig.exists():
      repoconfig.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    for repo in self.getAllRepos():
      
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
  
  def error(self, e):
    self.dsdir.rm(recursive=True, force=True)


EVENTS = {'MAIN': [PkglistEvent]}

#------ ERRORS ------#
class DepSolveError(StandardError): pass
