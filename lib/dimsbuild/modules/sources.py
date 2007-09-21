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


class SourcesRepomdEvent(Event):
  "Downloads and reads the repomd.xml for each of the source repositories."
  def __init__(self):    
    Event.__init__(self,
                   id='source-repomd',
                   provides=['source-repomd-files', 'source-repos',
                             'sources-enabled', 'local-source-repodata'])

    self.DATA = {
      'config': ['/distro/sources/repo'],
      'input':  [],
      'output': [],
    }
        
    self.cvars['sources-enabled'] = self.config.pathexists('/distro/sources') and \
               self.config.get('/distro/sources/@enabled', 'True') in BOOLEANS_TRUE

  def validate(self):
    self.validator.validate('/distro/sources', 'sources.rng')

  def setup(self):
    self.setup_diff(self.DATA)
    if not self.cvars['sources-enabled']: return

    self.srcrepos = {}    
    for repoxml in self.config.xpath('/distro/sources/repo'):
      # create repo object
      repo = RepoFromXml(repoxml)
      repo.local_path = self.mddir / repo.id
      repo.pkgsfile = repo.local_path / 'packages'

      self.srcrepos[repo.id] = repo
      # add repodata folder as input/output
      self.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'),
                      paths=[repo.rjoin(repo.repodata_path, repo.mdfile)],
                      id='%s-repomd' % repo.id)

  def run(self):
    if not self.cvars['sources-enabled']:
      self.remove_output(all=True)
      self.write_metadata() 
      return
    self.log(0, L0("processing source repositories"))

    backup = self.files_callback.sync_start
    self.files_callback.sync_start = self._print_nothing
    
    for repo in self.srcrepos.values():
      self.log(1, repo.id)
      self.sync_input(what='%s-repomd' % repo.id)
    
    self.files_callback.sync_start = backup

    self.write_metadata() 
  
  def _print_nothing(self):
    pass
  
  def apply(self):
    if self.cvars['sources-enabled']:
      self.cvars['local-source-repodata'] = self.mddir
      if not self.cvars['source-repos']:
        self.cvars['source-repos'] = {}
      self.cvars['source-repos'].update(self.srcrepos)
      self.cvars['source-repomd-files'] = []
      for repo in self.srcrepos.values():
        repomd = repo.ljoin(repo.repodata_path, repo.mdfile)
        if not repomd.exists():
          raise RuntimeError("Unable to find cached file at '%s'. Perhaps "
                             "you are skipping the source-repomd event before "
                             "it has been allowed to run once?" % repomd)
        self.cvars['source-repomd-files'].append(repomd)
        repo.readRepoData(xmltree.read(repomd).xpath('//data'))


class SourcesContentEvent(Event):
  "Downloads and reads the primary.xml.gz for each of the source repositories." 
  def __init__(self):    
    Event.__init__(self,
                   id='source-repo-contents',
                   provides=['source-repo-contents'],
                   comes_after=['source-repomd'])
    self.DATA = {
      'variables': ['cvars[\'sources-enabled\']'],
      'input':  [],
      'output': [],
    }

  def setup(self):
    self.setup_diff(self.DATA)

    if not self.cvars['sources-enabled']: return
    
    for repo in self.cvars['source-repos'].values():
      paths = []      
      for fileid in repo.datafiles:
        paths.append(repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles[fileid]))
      self.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'),
                      paths=paths, id='%s-files' % repo.id)

  def run(self):
    if not self.cvars['sources-enabled']:
      self.remove_output(all=True)
      self.write_metadata()
      return
    self.log(0, "downloading information about source packages")
    
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda: None
    
    # download primary.xml.gz etc.
    for repo in self.cvars['source-repos'].values():
      self.log(1, repo.id)
      self.sync_input(what='%s-files' % repo.id)
    
    self.files_callback.sync_start = backup
    
    # reading primary.xml.gz files
    self.log(1, "reading available source packages")
    for repo in self.cvars['source-repos'].values():
      pxml = repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles['primary'])
      if self._diff_handlers['input'].diffdict.has_key(pxml):
        self.log(2, repo.id)
        repo.readRepoContents()
        repo.writeRepoContents(repo.pkgsfile)
        self.DATA['output'].append(repo.pkgsfile)

    self.write_metadata()
  
  def apply(self):
    if not self.cvars['sources-enabled']: return
    for repo in self.cvars['source-repos'].values():
      if not repo.pkgsfile.exists():
        raise RuntimeError("Unable to find cached file at '%s'. Perhaps you "
                           "are skipping the repo-contents event before it "
                           "has been allowed to run once?" % repo.pkgsfile)
      repo.readRepoContents(repofile=repo.pkgsfile)


class SourcesEvent(Event):
  "Downloads source rpms."
  def __init__(self):
    Event.__init__(self,
                   id='sources',
                   comes_after=['source-repo-contents'],
                   provides=['srpms'],
                   requires=['rpms', 'source-repo-contents'])

    self.srpmdest = self.OUTPUT_DIR / 'SRPMS'
    self.DATA = {
      'variables': ['cvars[\'rpms\']',
                    'cvars[\'sources-enabled\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
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
    
    self.setup_sync(self.srpmdest, paths=paths, id='srpms')

  def run(self):
    if not self.cvars['sources-enabled']:
      self.remove_output(all=True)
      self.write_metadata()
      return
    
    self.log(0, L0("processing srpms"))
    self.remove_output()
    self.srpmdest.mkdirs()
    self.sync_input()
    self._createrepo()
    self.DATA['output'].extend(self.list_output(what=['srpms']))
    self.DATA['output'].append(self.srpmdest/'repodata')
    self.write_metadata()

  def apply(self):
    if self.cvars['sources-enabled']:
      self.cvars['srpms'] = self.list_output(what='srpms')
   
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


EVENTS = {'MAIN': [SourcesRepomdEvent, SourcesContentEvent, SourcesEvent]}
