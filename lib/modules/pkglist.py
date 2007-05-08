from os.path import join, exists

import dims.depsolver  as depsolver
import dims.filereader as filereader
import dims.osutils    as osutils

from dims.repocreator import YumRepoCreator

from callback  import BuildDepsolveCallback
from event     import EVENT_TYPE_PROC, EVENT_TYPE_MDLR
from interface import EventInterface

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'repogen',
    'interface': 'EventInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['repoconfig'],
    'requires': ['comps.xml', 'stores', 'RPMS'],
  },
  {
    'id': 'pkglist',
    'interface': 'PkglistInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pkglist'],
    'requires': ['comps.xml', 'stores', 'repoconfig'],
  },
]

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
  '',
]

class PkglistInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)
  
  def getRequiredPackages(self):
    return self._base.reqpkgs
  def getPkglist(self):
    try:
      return self._base.pkglist
    except AttributeError:
      return None
  def setPkglist(self, pkglist):
    self._base.pkglist = pkglist

def init_hook(interface):
  parser = interface.getOptParser('build')
  
  # the following option doesn't work yet
  parser.add_option('--with-pkglist',
                    default=None,
                    dest='with_pkglist',
                    metavar='PKGLISTFILE',
                    help='use PKGLISTFILE for the pkglist instead of generating it')

class DepsolveMDCreator(YumRepoCreator):
  "A subclass of YumRepoCreator that handles making the depsolve config file"
  def __init__(self, yumrepo, config, fallback):
    YumRepoCreator.__init__(self, yumrepo, config, fallback)
  
  def getPath(self, storeQuery):
    path = self.config.eget(join(storeQuery, 'path/text()'))
    mdpath = self.config.eget(join(storeQuery, 'repodata-path/text()'), None)
    if mdpath is not None:
      path = join(path, mdpath)
    
    return path

#def applyopt_hook(interface):
#  interface.setEventControlOption('pkglist', interface.options.do_pkglist)

def prerepogen_hook(interface):
  interface.set_cvar('repoconfig', False)

def repogen_hook(interface):
  cfgfile = join(interface.getTemp(), 'depsolve')
  
  dmdc = DepsolveMDCreator(cfgfile,
                       interface.config.file,
                       fallback='//stores')
  dmdc.createRepoFile()
  
  conf = filereader.read(cfgfile)
  conf = YUMCONF_HEADER + conf
  filereader.write(conf, cfgfile)
  
  interface.set_cvar('repoconfig', cfgfile)

def prepkglist_hook(interface):
  interface.disableEvent('pkglist')
  if interface.get_cvar('inputstore-changed') or interface.get_cvar('comps-changed'):
    interface.enableEvent('pkglist')
  elif not exists(join(interface.getMetadata(), 'pkglist')) and \
          interface.getPkglist() is None:
    interface.enableEvent('pkglist')
  interface.set_cvar('pkglist-changed', False)

def pkglist_hook(interface):
  interface.log(0, "resolving pkglist")
  interface.log(1, "generating new pkglist")
  
  cfgfile = interface.get_cvar('repoconfig')
  if not cfgfile: raise RuntimeError, 'repoconfig is not set'
  
  osutils.mkdir(join(interface.getMetadata(), '.depsolve'))
  
  pkgtups = depsolver.resolve(interface.getRequiredPackages(),
                              root=join(interface.getMetadata(), '.depsolve'),
                              config=cfgfile,
                              arch=interface.arch,
                              callback=BuildDepsolveCallback(interface.logthresh))
  
  # verify that final package list contains all user-specified packages
  interface.log(1, "verifying package list")
  nlist = [ n for n,_,_,_,_ in pkgtups ] # extract pkg names for checking
  for pcheck in interface.get_cvar('required-packages', []):
    if pcheck not in nlist:
      raise DepSolveError, "User-specified package '%s' not found in resolved pkglist" % pcheck
  del nlist
  
  interface.log(1, "pkglist closure achieved @ %s packages" % len(pkgtups))
  
  pkglist = []
  for n,_,_,v,r in pkgtups:
    pkglist.append('%s-%s-%s' % (n,v,r))
  pkglist.sort()

  interface.setPkglist(pkglist)
  interface.set_cvar('pkglist-changed', True)

  
def postpkglist_hook(interface):
  if interface.getPkglist() is None:
    interface.setPkglist(filereader.read(join(interface.getMetadata(), 'pkglist')))
  else:
    interface.log(1, "writing pkglist")
    filereader.write(interface.getPkglist(), join(interface.getMetadata(), 'pkglist'))
  osutils.rm(interface.get_cvar('repoconfig'), force=True)

class DepSolveError(StandardError): pass
