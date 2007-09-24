""" 
sources.py

downloads srpms 
"""

import os
import re
import rpm
import stat

from dims import dispatch
from dims import pps
from dims import shlib 
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB, SRPM_PNVRA
from dimsbuild.event     import Event
from dimsbuild.logging   import L0, L1, L2
from dimsbuild.repo      import RepoFromXml

P = pps.Path

API_VERSION = 5.0

SRPM_PNVRA_REGEX = re.compile(SRPM_PNVRA)

class SourceReposEvent(Event):
  "Downloads and reads the primary.xml.gz for each of the source repositories." 
  def __init__(self):    
    Event.__init__(self,
                   id='source-repos',
                   provides=['sources-enabled', 'source-repos'])
    self.DATA = {
      'variables': ['cvars[\'sources-enabled\']'],
      'input':  [],
      'output': [],
    }

    self.cvars['sources-enabled'] = self.config.pathexists('/distro/sources') and \
               self.config.get('/distro/sources/@enabled', 'True') in BOOLEANS_TRUE

  def validate(self):
    self.validator.validate('/distro/sources', 'sources.rng')

  def setup(self):
    self.diff.setup(self.DATA)

    if not self.cvars['sources-enabled']: return
 
    self.source_repos = {}    

    for repo in self.config.xpath('/distro/sources/repo'):
      repo = RepoFromXml(repo)
      repo.local_path = self.mddir/repo.id
      repo.readRepoData(tmpdir=self.TEMP_DIR)
      repo.pkgsfile = self.mddir / repo.id / 'packages'
      self.source_repos[repo.id] = repo
      
      paths = []      
      for fileid in repo.datafiles:
        paths.append(repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles[fileid]))
      paths.append(repo.rjoin(repo.repodata_path, repo.mdfile))
      self.io.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'),
                      paths=paths, id='%s-files' % repo.id)

  def run(self):
    self.log(0, L0("running source-repos event"))

    if not self.cvars['sources-enabled']:
      self.io.remove_output(all=True)
      self.diff.write_metadata()
      return
    
    self.log(1, L1("downloading information about source packages"))
    
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda: None
    
    # download primary.xml.gz etc.
    for repo in self.source_repos.values():
      self.log(1, L1(repo.id))
      self.io.sync_input(what='%s-files' % repo.id)
    
    self.files_callback.sync_start = backup
    
    # reading primary.xml.gz files
    self.log(1, L1("reading available source packages"))
    for repo in self.source_repos.values():
      pxml = repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles['primary'])
      if self.diff.handlers['input'].diffdict.has_key(pxml):
        self.log(2, L2(repo.id))
        repo.readRepoContents()
        repo.writeRepoContents(repo.pkgsfile)
        self.DATA['output'].append(repo.pkgsfile)

    self.diff.write_metadata()
  
  def apply(self):
    if not self.cvars['sources-enabled']: return
    for repo in self.source_repos.values():
      if not repo.pkgsfile.exists():
        raise RuntimeError("Unable to find cached file at '%s'. Perhaps you "
                           "are skipping the repo-contents event before it "
                           "has been allowed to run once?" % repo.pkgsfile)
      repo.readRepoContents(repofile=repo.pkgsfile)

    self.cvars['source-repos'] = self.source_repos

class SourcesEvent(Event):
  "Downloads source rpms."
  def __init__(self):
    Event.__init__(self,
                   id='sources',
                   provides=['srpms'],
                   requires=['rpms', 'source-repos'])

    self.srpmdest = self.OUTPUT_DIR / 'SRPMS'
    self.DATA = {
      'variables': ['cvars[\'rpms\']',
                    'cvars[\'sources-enabled\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

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
    for repo in self.cvars['source-repos'].values():
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
    
    self.io.setup_sync(self.srpmdest, paths=paths, id='srpms')

  def run(self):
    self.log(0, L0("running sources event"))
 
    if not self.cvars['sources-enabled']:
      self.io.remove_output(all=True)
      self.diff.write_metadata()
      return
    
    self.log(1, L1("processing srpms"))
    self.io.remove_output()
    self.srpmdest.mkdirs()
    self.io.sync_input()
    self._createrepo()
    self.DATA['output'].extend(self.io.list_output(what=['srpms']))
    self.DATA['output'].append(self.srpmdest/'repodata')
    self.diff.write_metadata()

  def apply(self):
    if self.cvars['sources-enabled']:
      self.cvars['srpms'] = self.io.list_output(what='srpms')
   
  def _deformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, L2("DEBUG: Unable to extract srpm information from name '%s'" % srpm))
      return (None, None, None, None, None)
  
  def _createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.srpmdest)
    self.log(1, L1("running createrepo"))
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)


EVENTS = {'MAIN': [SourceReposEvent, SourcesEvent]}
