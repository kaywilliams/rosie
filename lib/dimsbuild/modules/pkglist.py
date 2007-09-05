from dims import depsolver
from dims import filereader

from dimsbuild.callback  import BuildDepsolveCallback
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'pkglist',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pkglist'],
    'requires': ['required-packages', 'local-repodata'],
    'conditional-requires': ['user-required-packages'],
  },
]

HOOK_MAPPING = {
  'PkglistHook':  'pkglist',
  'ValidateHook': 'validate',
}

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

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.validate'

    self.interface = interface

  def run(self):
    self.interface.validate('/distro/pkglist', schemafile='pkglist.rng')


class PkglistHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.pkglist'
    
    self.interface = interface
    
    self.mddir = self.interface.METADATA_DIR / 'pkglist'
    self.dsdir = self.mddir / '.depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['/distro/pkglist'],
      'variables': ['cvars[\'required-packages\']'],
      'input':     [],
      'output':    [], 
    }
    self.mdfile = self.mddir / 'pkglist.md'
    self.docopy = self.interface.config.pathexists('/distro/pkglist/text()')
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    # setup if copying pkglist
    if self.docopy:
      self.interface.setup_sync(self.mddir, id='pkglist',
                                xpaths=['/distro/pkglist'])
      self.pkglistfile = self.interface.list_output(what='pkglist')[0]
      return

    # setup if creating pkglist
    self.pkglistfile = self.mddir / 'pkglist'
    self.DATA['output'].append(self.pkglistfile)

    self.rddirs = [] # list of repodata dirs across all repos

    for repo in self.interface.getAllRepos():
      self.rddirs.append(repo.ljoin(repo.repodata_path, 'repodata'))

    self.DATA['input'].extend(self.rddirs)

  def clean(self):
    self.interface.log(0, "cleaning pkglist event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    if not self.mddir.exists(): self.mddir.mkdirs()

    self.interface.log(0, "resolving pkglist")
    self.interface.remove_output(all=True)

    # copy pkglist    
    if self.docopy:
      self.interface.sync_input()
      self.interface.log(1, "reading supplied pkglist file")
      if self.dsdir.exists():
        self.dsdir.rm(recursive=True)
      self.interface.write_metadata()
      return

    # create pkglist
    self.interface.log(1, "generating new pkglist")
    if not self.dsdir.exists(): self.dsdir.mkdirs()
      
    repoconfig = self.create_repoconfig()
    pkgtups = depsolver.resolve(
      self.interface.cvars['required-packages'] or [],
      root=str(self.dsdir), # yum is much happier if these are strings
      config=str(repoconfig), # this too
      arch=self.interface.arch,
      callback=BuildDepsolveCallback(self.interface.logthresh)
    )
    repoconfig.remove()
      
    # verify that final package list contains all user-specified packages
    self.interface.log(1, "verifying package list")
    nlist = [ n for n,_,_,_,_ in pkgtups ] # extract pkg names for checking
    for pcheck in self.interface.cvars.get('user-required-packages', []):
      if pcheck not in nlist:
        raise DepSolveError("User-specified package '%s' not found in resolved pkglist" % pcheck)
    del nlist
      
    self.interface.log(1, "pkglist closure achieved in %d packages" % len(pkgtups))

    pkglist = []
    for n,_,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s' % (n,v,r))
    pkglist.sort()
      
    self.interface.log(1, "writing pkglist")        
    filereader.write(pkglist, self.pkglistfile)

    self.interface.write_metadata()

  def create_repoconfig(self):
    repoconfig = self.interface.TEMP_DIR / 'depsolve.repo'
    if repoconfig.exists():
      repoconfig.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    for repo in self.interface.getAllRepos():

      # determine if repodata folder changed
      rddir_changed = False
      for rddir in self.rddirs:
        for file in self.interface.handlers['input'].diffdict.keys():
          if file.startswith(rddir):
            rddirs_changed = True
            break
 
      if rddir_changed: 
        ## HACK: delete a folder's depsolve metadata if it has changed. 
        (self.dsdir/repo.id).rm(recursive=True, force=True)

      conf.extend([
        '[%s]' % repo.id,
        'name = %s' % repo.id,
        'baseurl = file://%s' % repo.local_path,
        '\n',
      ])
    filereader.write(conf, repoconfig)
    return repoconfig
   
  def apply(self):
    if not self.pkglistfile.exists():
      raise RuntimeError("missing package list file: '%s'" % self.pkglistfile)
    self.interface.cvars['pkglist'] = filereader.read(self.pkglistfile)
  
#------ ERRORS ------#
class DepSolveError(StandardError): pass
