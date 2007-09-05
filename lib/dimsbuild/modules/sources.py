""" 
sources.py

downloads srpms 
"""

import os
import re
import rpm

from dims import pps
from dims import shlib 
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB, SRPM_PNVRA
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import EventInterface, RepoFromXml

P = pps.Path

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'source-repos',
    'provides': ['local-source-repodata',
                 'source-repo-contents',
                 'sources-enabled'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
  {
    'id': 'sources',
    'provides': ['srpms',],
    'requires': ['rpms', 'source-repo-contents'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
]

HOOK_MAPPING = {
  'SourcesHook':    'sources',
  'ValidateHook':   'validate',
  'SourceRepoHook': 'source-repos',
}

SRPM_PNVRA_REGEX = re.compile(SRPM_PNVRA)

class SrpmInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)    
    self.srpmdest = self.OUTPUT_DIR/'SRPMS'
    
  def getAllSourceRepos(self):
    return self.cvars['source-repos'].values()
  
  def deformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract srpm information from name '%s'" % srpm)
      return (None, None, None, None, None)

  def nvr(self, srpm):
    "nvr = SoftwareInterface.nvr(rpm) - convert an RPM filename into an NVR string"
    _,n,v,r,_ = self.deformat(srpm)
    return '%s-%s-%s' % (n,v,r)    

  def createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.srpmdest)
    self.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/sources', 'sources.rng')
    
class SourceRepoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source-repos'
    self.interface = interface

    self.mdsrcrepos = self.interface.METADATA_DIR/'source-repos'

    self.interface.cvars['sources-enabled'] = \
       self.interface.config.pathexists('/distro/sources') and \
       self.interface.config.get('/distro/sources/@enabled', 'True') in BOOLEANS_TRUE
    
    self.DATA = {
      'variables': ['cvars[\'sources-enabled\']'],
      'config':    ['/distro/sources'],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.interface.METADATA_DIR/'source-repos.md'

  def setup(self):    
    self.interface.setup_diff(self.mdfile, self.DATA)
    if not self.interface.cvars['sources-enabled']: return

    self.srcrepos = {}
    self.mdsrcrepos.mkdirs()
    
    for repoxml in self.interface.config.xpath('/distro/sources/repo'):
      repo = RepoFromXml(repoxml)
      repo.local_path = self.mdsrcrepos/repo.id
      repo.pkgsfile = self.mdsrcrepos/'%s.pkgs' % repo.id
        
      self.interface.setup_sync(repo.ljoin(repo.repodata_path),
                                paths=[repo.rjoin(repo.repodata_path,
                                                  'repodata')])
      self.DATA['output'].append(repo.pkgsfile)
    
      self.srcrepos[repo.id] = repo

      self.DATA['output'].append(repo.ljoin(repo.repodata_path, 'repodata'))
      self.DATA['output'].append(self.interface.METADATA_DIR/'%s.pkgs' % repo.id)
      self.srcrepos[repo.id] = repo

  def clean(self):
    self.interface.log(0, "cleaning source-repos event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    # changing from sources-enabled true, cleanup old files and metadata
    if self.interface.var_changed_from_true('cvars[\'sources-enabled\']'):
      self.clean()

    if not self.interface.cvars['sources-enabled']: 
      self.interface.write_metadata()
      return

    self.interface.log(0, "processing source repositories")
    self.interface.sync_input()

    self.interface.log(1, "reading available packages")
    self.interface.repoinfo = {}
    for repo in self.srcrepos.values():
      self.interface.log(2, repo.id)

      # read repomd.xml
      repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
      repo.readRepoData(repomd)

      # read primary.xml
      repo.readRepoContents()
      repo.writeRepoContents(repo.pkgsfile)

    self.interface.write_metadata() 
    
  def apply(self):
    self.interface.cvars['local-source-repodata'] = self.mdsrcrepos
    if self.interface.cvars['sources-enabled']:
      self.interface.cvars['source-repos'] = self.srcrepos
      for repo in self.srcrepos.values():
        repomdfile = repo.ljoin(repo.repodata_path, repo.mdfile)
        for file in repomdfile, repo.pkgsfile:
          if not file.exists():
            raise RuntimeError("Unable to find cached file at '%s'. Perhaps you " \
                               "are skipping the 'source-repos' event before it has "\
                               "been allowed to run once?" % file)
        repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
        repo.readRepoData(repomd)
        repo.readRepoContents(repofile=repo.pkgsfile)

class SourcesHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.sources'
    
    self.interface = interface
    
    self.DATA =  {
      'variables':['cvars[\'sources-enabled\']',
                   'cvars[\'rpms\']'], 
      'input':    [],
      'output':   [],
    }
    self.mdfile = self.interface.METADATA_DIR/'source.md'
      
  def setup(self):
    self.mdsrcrepos = self.interface.cvars['local-source-repodata']    
    
    self.interface.setup_diff(self.mdfile, self.DATA)

    if not self.interface.cvars['sources-enabled']: return

    # compute the list of SRPMS
    self.ts = rpm.TransactionSet()
    self.ts.setVSFlags(-1)    
    srpmlist = []
    for pkg in self.interface.cvars['rpms']:
      i = os.open(pkg, os.O_RDONLY)
      h = self.ts.hdrFromFdno(i)
      os.close(i)
      srpm = h[rpm.RPMTAG_SOURCERPM]
      if srpm not in srpmlist:
        srpmlist.append(srpm)

    # setup sync
    paths = []
    for repo in self.interface.getAllSourceRepos():
      for rpminfo in repo.repoinfo:
        rpmi = rpminfo['file']
        _,n,v,r,a = self.interface.deformat(rpmi)
        nvra = '%s-%s-%s.%s.rpm' %(n,v,r,a) ## assuming the prefix to be lower-case 'rpm' suffixed
        if nvra in srpmlist:
          paths.append(rpmi)

    self.interface.setup_sync(self.interface.srpmdest, paths=paths, id='srpms')

  def clean(self):
    self.interface.log(0, "cleaning sources event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()  

  def run(self):
    # changing from sources-enabled true, cleanup old files and metadata
    if self.interface.var_changed_from_true('cvars[\'sources-enabled\']'):
      self.clean()

    if not self.interface.cvars['sources-enabled']: 
      self.interface.write_metadata()
      return

    self.interface.log(0, "processing srpms")
    self.interface.remove_output()
    self.interface.srpmdest.mkdirs()
    self.interface.sync_input()
    self.interface.createrepo()
    self.DATA['output'].extend(self.interface.list_output(what=['srpms']))
    self.DATA['output'].append(self.interface.srpmdest/'repodata')

    self.interface.write_metadata()

  def apply(self):
    if self.interface.cvars['sources-enabled']:
      self.interface.cvars['srpms'] = self.interface.list_output(what=['srpms'])
