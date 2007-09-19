""" 
sources.py

downloads srpms 
"""

import os
import re
import rpm
import stat

from dims import pps
from dims import shlib 
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB, SRPM_PNVRA
from dimsbuild.event     import Event
from dimsbuild.repo      import RepoFromXml

P = pps.Path

API_VERSION = 5.0

SRPM_PNVRA_REGEX = re.compile(SRPM_PNVRA)

class SourcesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'sources',
      provides = ['local-source-repodata',
                  'source-repo-contents',
                  'sources-enabled'],
    )
    
    self.cvars['sources-enabled'] = \
       self.config.pathexists('/distro/sources') and \
       self.config.get('/distro/sources/@enabled', 'True') in BOOLEANS_TRUE
    
    self.DATA = {
      'variables': ['cvars[\'sources-enabled\']'],
      'config':    ['/distro/sources'],
      'input':     [],
      'output':    [],
    }
  
  def validate(self):
    self._validate('/distro/sources', 'sources.rng')

  def setup(self):    
    self.setup_diff(self.DATA)
    if not self.cvars['sources-enabled']: return
    
    self.srcrepos = {}
    
    for repoxml in self.config.xpath('/distro/sources/repo'):
      repo = RepoFromXml(repoxml)
      repo.local_path = self.mddir/repo.id
      repo.pkgsfile = self.mddir/'%s.pkgs' % repo.id
        
      self.setup_sync(repo.ljoin(repo.repodata_path),
                      paths=[repo.rjoin(repo.repodata_path,
                                        'repodata')])
      self.DATA['output'].append(repo.pkgsfile)
      
      self.srcrepos[repo.id] = repo
      
      self.DATA['output'].append(repo.ljoin(repo.repodata_path, 'repodata'))
      self.DATA['output'].append(repo.pkgsfile)
      self.srcrepos[repo.id] = repo
  
  def run(self):
    # changing from sources-enabled true, cleanup old files and metadata
    if self.var_changed_from_value('cvars[\'sources-enabled\']', True):
      self.clean()

    if not self.cvars['sources-enabled']: 
      self.write_metadata()
      return
    
    self.log(0, "processing source repositories")
    self.sync_input()
    
    self.log(1, "reading available packages")
    self.repoinfo = {}
    for repo in self.srcrepos.values():
      self.log(2, repo.id)
      
      # read repomd.xml
      repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
      repo.readRepoData(repomd)
      
      # read primary.xml
      repo.readRepoContents()
      repo.writeRepoContents(repo.pkgsfile)
    
    self.write_metadata() 
  
  def apply(self):
    self.cvars['local-source-repodata'] = self.mddir
    if self.cvars['sources-enabled']:
      self.cvars['source-repos'] = self.srcrepos
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


class SourceReposEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'source-repos',
      provides = ['srpms'],
      requires = ['rpms', 'source-repo-contents'],
    )
      
    self.srpmdest = self.OUTPUT_DIR/'SRPMS'
    
    self.DATA =  {
      'variables':['cvars[\'sources-enabled\']',
                   'cvars[\'rpms\']'], 
      'input':    [],
      'output':   [],
    }
    
  def setup(self):
    self.mdsrcrepos = self.cvars['local-source-repodata']    
    
    self.setup_diff(self.DATA)
    
    if not self.cvars['sources-enabled']: return
    
    # compute the list of SRPMS
    self.ts = rpm.TransactionSet()
    self.ts.setVSFlags(-1)
    
    srpmset = set()
    for pkg in self.cvars['rpms']:
      i = os.open(pkg, os.O_RDONLY)
      h = self.ts.hdrFromFdno(i)
      os.close(i)
      srpm = h[rpm.RPMTAG_SOURCERPM]
      srpmset.add(srpm)
    
    # setup sync
    paths = []
    for repo in self._getAllSourceRepos():
      for rpminfo in repo.repoinfo:
        rpmi = rpminfo['file']
        _,n,v,r,a = self._deformat(rpmi)
        ## assuming the rpm file name to be lower-case 'rpm' suffixed        
        nvra = '%s-%s-%s.%s.rpm' %(n,v,r,a) 
        if nvra in srpmset:
          rpmi = P(rpminfo['file'])
          if isinstance(rpmi, pps.path.http.HttpPath): #! bad
            rpmi._update_stat({'st_size':  rpminfo['size'],
                               'st_mtime': rpminfo['mtime'],
                               'st_mode':  stat.S_IFREG})
          paths.append(rpmi)
    
    self.setup_sync(self.srpmdest, paths=paths, id='srpms')
  
  def run(self):
    # changing from sources-enabled true, cleanup old files and metadata
    if self.var_changed_from_value('cvars[\'sources-enabled\']', True):
      self.clean()
    
    if not self.cvars['sources-enabled']: 
      self.write_metadata()
      return
    
    self.log(0, "processing srpms")
    self.remove_output()
    self.srpmdest.mkdirs()
    self.sync_input()
    self._createrepo()
    self.DATA['output'].extend(self.list_output(what=['srpms']))
    self.DATA['output'].append(self.srpmdest/'repodata')
    
    self.write_metadata()
  
  def apply(self):
    if self.cvars['sources-enabled']:
      self.cvars['srpms'] = self.list_output(what=['srpms'])
  
  
  def _getAllSourceRepos(self):
    return self.cvars['source-repos'].values()
  
  def _deformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract srpm information from name '%s'" % srpm)
      return (None, None, None, None, None)
  
  def _createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.srpmdest)
    self.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)


EVENTS = {'MAIN': [SourceReposEvent, SourcesEvent]}
