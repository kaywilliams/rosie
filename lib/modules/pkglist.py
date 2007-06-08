from os.path import join, exists

from dims import depsolver
from dims import filereader
from dims import listcompare
from dims import osutils

from dims.repocreator import YumRepoCreator

from callback  import BuildDepsolveCallback
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'repogen',
    'properties': EVENT_TYPE_PROC,
    'provides': ['repoconfig'],
    'conditional-requires': ['comps.xml', 'RPMS'],
  },
  {
    'id': 'pkglist',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pkglist'],
    'requires': ['required-packages', 'repoconfig'],
    'conditional-requires': ['stores', 'user-required-packages'],
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
  'RepogenHook':  'repogen',
  'PkglistHook':  'pkglist',
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


class DepsolveMDCreator(YumRepoCreator):
  "A subclass of YumRepoCreator that handles making the depsolve config file"
  def __init__(self, yumrepo, config, fallback):
    YumRepoCreator.__init__(self, yumrepo, config, fallback)
  
  def getPath(self, storeQuery):
    path   = self.config.eget(join(storeQuery, 'path/text()'))
    mdpath = self.config.eget(join(storeQuery, 'repodata-path/text()'), None)
    if mdpath is not None:
      path = join(path, mdpath)
    return path


#------ HOOKS ------#
class InitHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.init'
    
    self.interface = interface
  
  def run(self):
    parser = self.interface.getOptParser('build')
    
    # the following option doesn't work yet
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
      self.interface.set_cvar('pkglist-file', self.interface.options.with_pkglist)

class RepogenHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.repogen'
    
    self.interface = interface
    
    self.cfgfile = join(self.interface.TEMP_DIR, 'depsolve')
 
  def force(self):
    osutils.rm(self.cfgfile, force=True)
  
  def run(self):
    dmdc = DepsolveMDCreator(self.cfgfile, self.interface.config.file, fallback='//stores')
    dmdc.createRepoFile()
    
    conf = filereader.read(self.cfgfile)
    conf = YUMCONF_HEADER + conf
    filereader.write(conf, self.cfgfile)
  
  def apply(self):
    if not exists(self.cfgfile):
      raise RuntimeError, "Unable to find depsolve config file at '%s'" % self.cfgfile
    self.interface.set_cvar('repoconfig-file', self.cfgfile)

class PkglistHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.pkglist'
    
    self.interface = interface
    
    self.mddir = join(self.interface.METADATA_DIR, '.depsolve')
    self.pkglistfile = join(self.interface.METADATA_DIR, 'pkglist')
  
  def force(self):
    osutils.rm(self.mddir, recursive=True, force=True)
    osutils.rm(self.pkglistfile, force=True)
  
  def run(self):
    if not self._test_runstatus(): return # check to make sure we should be running
    
    self.interface.log(0, "resolving pkglist")
    
    pkglist = []
    pkglistfile = self.interface.get_cvar('pkglist-file', None)
    if pkglistfile is not None:
      self.interface.log(1, "reading supplied pkglist file '%s'" % pkglistfile)
      pkglist = filereader.read(pkglistfile)
    else:
      self.interface.log(1, "generating new pkglist")
      
      cfgfile = self.interface.get_cvar('repoconfig-file')
      if not cfgfile: raise RuntimeError, 'repoconfig-file is not set'
      
      osutils.mkdir(self.mddir)
      
      pkgtups = depsolver.resolve(self.interface.get_cvar('required-packages', []),
                                  root=self.mddir,
                                  config=cfgfile,
                                  arch=self.interface.arch,
                                  callback=BuildDepsolveCallback(self.interface.logthresh))
      
      
      # verify that final package list contains all user-specified packages
      self.interface.log(1, "verifying package list")
      nlist = [ n for n,_,_,_,_ in pkgtups ] # extract pkg names for checking
      for pcheck in self.interface.get_cvar('user-required-packages', []):
        if pcheck not in nlist:
          print self.interface.get_cvar('user-required-packages', [])
          raise DepSolveError, "User-specified package '%s' not found in resolved pkglist" % pcheck
      del nlist
      
      self.interface.log(1, "pkglist closure achieved in %d packages" % len(pkgtups))
    
      for n,_,_,v,r in pkgtups:
        pkglist.append('%s-%s-%s' % (n,v,r))
    
    pkglist.sort()
    
    if exists(self.pkglistfile):
      oldpkglist = filereader.read(self.pkglistfile)
    else:
      oldpkglist = []
    oldpkglist.sort()
    
    old,new,_ = listcompare.compare(oldpkglist, pkglist)
    if len(new) > 0 or len(old) > 0:
      self.interface.log(1, "package list has changed")
      self.interface.set_cvar('pkglist-changed', True)
      if pkglistfile is None:
        self.interface.log(1, "writing pkglist")
        filereader.write(pkglist, self.pkglistfile)
    else:
      self.interface.log(1, "package list unchanged")
  
  def apply(self):
    if self.interface.get_cvar('pkglist-file'):
      if not exists(self.interface.get_cvar('pkglist-file')):
        raise RuntimeError, "Unable to find pkglist at '%s'" % self.interface.get_cvar('pkglist-file')
      else:
        if self.interface.get_cvar('pkglist-file') != self.pkglistfile:
          osutils.cp(self.interface.get_cvar('pkglist-file'), self.pkglistfile)
    else:
      self.interface.set_cvar('pkglist-file', self.pkglistfile)
    
    # read in package list
    self.interface.set_cvar('pkglist', filereader.read(self.interface.get_cvar('pkglist-file')))
  
  def post(self):
    # clean up metadata
    repoconfig = self.interface.get_cvar('repoconfig-file')
    if repoconfig: osutils.rm(repoconfig, force=True)
    
  def _test_runstatus(self):
    return self.interface.isForced('pkglist') or \
           self.interface.get_cvar('pkglist-file') or \
           self.interface.get_cvar('input-store-changed') or \
           self.interface.get_cvar('comps-changed') or \
           not exists(self.pkglistfile) and not self.interface.get_cvar('pkglist-file')


#------ ERRORS ------#
class DepSolveError(StandardError): pass
