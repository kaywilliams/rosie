import re

from os.path import join, exists

from dims import depsolver
from dims import filereader
from dims import listcompare
from dims import osutils

from dims.repocreator import YumRepoCreator

from dimsbuild.callback import BuildDepsolveCallback
from dimsbuild.event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'repogen',
    'properties': EVENT_TYPE_PROC,
    'provides': ['repoconfig-file'],
    'conditional-requires': ['comps-changed', 'RPMS'],
  },
  {
    'id': 'pkglist',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pkglist-file', 'pkglist', 'pkglist-changed'],
    'requires': ['required-packages', 'repoconfig-file', 'local-repodata'],
    'conditional-requires': ['user-required-packages', 'input-repos-changed'],
  },
]

HOOK_MAPPING = {
  'InitHook':     'init',
  'ApplyoptHook': 'applyopt',
  'RepogenHook':  'repogen',
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


class DepsolveMDCreator(YumRepoCreator):
  "A subclass of YumRepoCreator that handles making the depsolve config file"
  def __init__(self, yumrepo, config, fallback, repos):
    YumRepoCreator.__init__(self, yumrepo, config, fallback)
    
    self.repos = repos
    
    self.idre = re.compile('.*\[@id="(.*)"\].*')
  
  def getPath(self, repoQuery):
    repoid = self.idre.match(repoQuery).groups()[0]
    repo = self.repos[repoid]
    return 'file://' + repo.ljoin(repo.repodata_path)


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
    self.interface.validate('//pkglist', schemafile='pkglist.rng')
    

class RepogenHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'pkglist.repogen'
    
    self.interface = interface
    
    self.cfgfile = join(self.interface.TEMP_DIR, 'depsolve')
 
  def force(self):
    osutils.rm(self.cfgfile, force=True)
  
  def run(self):
    dmdc = DepsolveMDCreator(self.cfgfile, self.interface.config.file,
                             fallback='//repos',
                             repos=self.interface.cvars['repos'])
    dmdc.createRepoFile()
    
    conf = filereader.read(self.cfgfile)
    conf = YUMCONF_HEADER + conf
    filereader.write(conf, self.cfgfile)
  
  def apply(self):
    if not exists(self.cfgfile):
      raise RuntimeError, "Unable to find depsolve config file at '%s'" % self.cfgfile
    self.interface.cvars['repoconfig-file'] = self.cfgfile


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
  
  def check(self):
    return self.interface.isForced('pkglist') or \
           self.interface.cvars['pkglist-file'] or \
           self.interface.cvars['input-repos-changed'] or \
           self.interface.cvars['comps-changed'] or \
           not exists(self.pkglistfile) and not self.interface.cvars['pkglist-file']
  
  def run(self):
    self.interface.log(0, "resolving pkglist")
    
    pkglist = []
    if self.interface.cvars['pkglist-file']:
      self.interface.log(1, "reading supplied pkglist file '%s'" % self.interface.cvars['pkglist-file'])
      pkglist = filereader.read(self.interface.cvars['pkglist-file'])
    else:
      self.interface.log(1, "generating new pkglist")
      
      if not self.interface.cvars['repoconfig-file']:
        raise RuntimeError, 'repoconfig-file is not set'
      
      osutils.mkdir(self.mddir)
      
      pkgtups = depsolver.resolve(self.interface.cvars['required-packages'] or [],
                                  root=self.mddir,
                                  config=self.interface.cvars['repoconfig-file'],
                                  arch=self.interface.arch,
                                  callback=BuildDepsolveCallback(self.interface.logthresh))
      
      
      # verify that final package list contains all user-specified packages
      self.interface.log(1, "verifying package list")
      nlist = [ n for n,_,_,_,_ in pkgtups ] # extract pkg names for checking
      for pcheck in (self.interface.cvars['user-required-packages'] or []):
        if pcheck not in nlist:
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
      self.interface.cvars['pkglist-changed'] = True
      if not self.interface.cvars['pkglist-file']:
        self.interface.log(1, "writing pkglist")
        filereader.write(pkglist, self.pkglistfile)
    else:
      self.interface.log(1, "package list unchanged")
  
  def apply(self):
    if self.interface.cvars['pkglist-file']:
      if not exists(self.interface.cvars['pkglist-file']):
        raise RuntimeError, "Unable to find pkglist at '%s'" % self.interface.cvars['pkglist-file']
      else:
        if self.interface.cvars['pkglist-file'] != self.pkglistfile:
          osutils.cp(self.interface.cvars['pkglist-file'], self.pkglistfile)
    else:
      self.interface.cvars['pkglist-file'] = self.pkglistfile
    
    # read in package list
    self.interface.cvars['pkglist'] = filereader.read(self.interface.cvars['pkglist-file'])
  
  def post(self):
    # clean up metadata
    repoconfig = self.interface.cvars['repoconfig-file']
    if repoconfig: osutils.rm(repoconfig, force=True)
    

#------ ERRORS ------#
class DepSolveError(StandardError): pass
