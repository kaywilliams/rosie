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
  interface.setFlag('repoconfig', False)

def repogen_hook(interface):
  cfgfile = join(interface.getTemp(), 'depsolve')
  
  dmdc = DepsolveMDCreator(cfgfile,
                       interface.config.file,
                       fallback='//stores')
  dmdc.createRepoFile()
  interface.setFlag('repoconfig', cfgfile)

def prepkglist_hook(interface):
  interface.disableEvent('pkglist')
  if interface.getFlag('inputstore-changed') or interface.getFlag('comps-changed'):
    interface.enableEvent('pkglist')
  elif not exists(join(interface.getMetadata(), 'pkglist')) and \
          interface.getPkglist() is None:
    interface.enableEvent('pkglist')
  interface.setFlag('pkglist-changed', False)

def pkglist_hook(interface):
  interface.log(0, "resolving pkglist")
  interface.log(1, "generating new pkglist")
  
  cfgfile = interface.getFlag('repoconfig')
  if not cfgfile: raise RuntimeError, 'repoconfig is not set'
  
  osutils.mkdir(join(interface.getMetadata(), '.depsolve'))
  
  conf = filereader.read(cfgfile)
  conf = YUMCONF_HEADER + conf
  filereader.write(conf, cfgfile)
  
  pkgtups = depsolver.resolve(interface.getRequiredPackages(),
                              root=join(interface.getMetadata(), '.depsolve'),
                              config=cfgfile,
                              arch=interface.arch,
                              callback=BuildDepsolveCallback(interface.logthresh))

  interface.log(1, "pkglist closure achieved @ %s packages" % len(pkgtups))
  osutils.rm(cfgfile, force=True)
  
  pkglist = []
  for n,_,_,v,r in pkgtups:
    pkglist.append('%s-%s-%s' % (n,v,r))
  pkglist.sort()

  interface.setPkglist(pkglist)
  interface.setFlag('pkglist-changed', True)

  
def postpkglist_hook(interface):
  if interface.getPkglist() is None:
    interface.setPkglist(filereader.read(join(interface.getMetadata(), 'pkglist')))
  else:
    interface.log(1, "writing pkglist")
    filereader.write(interface.getPkglist(), join(interface.getMetadata(), 'pkglist'))
