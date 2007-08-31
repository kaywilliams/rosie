from dims import depsolver
from dims import filereader

from dimsbuild.callback  import BuildDepsolveCallback
from dimsbuild.event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'pkglist',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pkglist-file', 'pkglist', 'pkglist-changed'],
    'requires': ['required-packages', 'local-repodata'],
    'conditional-requires': ['user-required-packages', 'input-repos-changed'],
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
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
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.init'
    
    self.interface = interface
  
  def run(self):
    parser = self.interface.getOptParser('build')
    
    parser.add_option('--with-pkglist',
                      default=None,
                      dest='with_pkglist',
                      metavar='PKGLISTFILE',
                      help='use PKGLISTFILE for the pkglist instead of generating it')


class ApplyoptHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.applyopt'
    
    self.interface = interface
  
  def run(self):
    if self.interface.options.with_pkglist is not None:
      self.interface.cvars['pkglist-file'] = self.interface.options.with_pkglist


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
    
    self.mddir = self.interface.METADATA_DIR / '.depsolve'
    self.pkglistfile = self.interface.METADATA_DIR / 'pkglist'

    self.DATA = {
      'config':    ['/distro/pkglist'],
      'variables': ['cvars[\'required-packages\']'],
      'output':    [], 
    }
    self.mdfile = self.interface.METADATA_DIR / 'pkglist.md'
    self.docopy = self.interface.config.pathexists('/distro/pkglist/path/text()')
    if self.docopy:
      self.DATA['input'] = []
  
  def clean(self):
    self.interface.log(0, "cleaning pkglist event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()
  
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    if self.docopy:
      o = self.interface.setup_sync(xpaths=[('/distro/pkglist/path',
                                             self.interface.METADATA_DIR)])
      self.DATA['output'].extend(o)
      assert len(o) == 1
      self.pkglistfile = o[0]
    else:
      self.pkglistfile = self.interface.METADATA_DIR / 'pkglist'
      self.DATA['output'].append(self.pkglistfile)
  
  def check(self):
    return self.interface.cvars['input-repos-changed'] or \
           self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "resolving pkglist")
    self.interface.remove_output(all=True)
    
    if self.docopy:
      self.interface.sync_input()
      self.interface.log(1, "reading supplied pkglist file")
      if self.mddir.exists():
        self.mddir.rm(recursive=True)
    else:
      self.interface.log(1, "generating new pkglist")
      self.mddir.mkdirs()
      
      repoconfig = self.create_repoconfig()
      pkgtups = depsolver.resolve(
        self.interface.cvars['required-packages'] or [],
        root=str(self.mddir), # yum is much happier if these are strings
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
      if repo.changed:
        ## HACK: delete a folder's depsolve metadata if it has changed. 
        (self.mddir/repo.id).rm(recursive=True, force=True)
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
    self.interface.cvars['pkglist-file'] = self.pkglistfile
    self.interface.cvars['pkglist'] = filereader.read(self.pkglistfile)
  
#------ ERRORS ------#
class DepSolveError(StandardError): pass
