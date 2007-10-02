from dims import listcompare
from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.logging   import L1, L2
from dimsbuild.repo      import RepoContainer

P = pps.Path

class ListCompareMixin:
  def __init__(self, lfn=None, rfn=None, bfn=None, cb=None):
    self.lfn = lfn
    self.rfn = rfn
    self.bfn = bfn
    self.cb  = cb
    
    self.l = None
    self.r = None
    self.b = None
  
  def compare(self, l1, l2):
    self.l, self.r, self.b = listcompare.compare(l1, l2)
    
    if len(self.b) > 0:
      if self.cb:
        self.cb.notify_both(len(self.b))
      if self.bfn:
        for i in self.b: self.bfn(i)
    if len(self.l) > 0:
      if self.cb:
        self.cb.notify_left(len(self.l))
      if self.lfn:
        for i in self.l: self.lfn(i)
    if len(self.r) > 0:
      if self.cb:
        self.cb.notify_right(len(self.r))
      if self.rfn:
        for i in self.r: self.rfn(i)

class RepoEventMixin:  
  def __init__(self):
    self.rc = RepoContainer()
    self.repos = self.rc.repos
  
  def read_config(self, xpath_query):
    for repo in self.config.xpath(xpath_query):
      repo = self.rc.add_repo(repo.get('@id'),
        local_path = self.mddir / repo.get('@id'),
        remote_path = P(repo.get('path/text()')),
        pkgsfile = self.mddir / repo.get('@id') / 'packages',
        gpgcheck = repo.get('gpgcheck/text()', 'False') in BOOLEANS_TRUE,
        gpgkeys = [ P(x) for x in repo.xpath('gpgkey/text()', []) ],
        repodata_path = repo.get('repodata-path/text()', ''),
        include = repo.xpath('include/package/text()', []),
        exclude = repo.xpath('exclude/package/text()', [])
      )
      repo.readRepoData(tmpdir=self.TEMP_DIR)

      paths = []
      for filetype in repo.datafiles.keys():
        paths.append(repo.rjoin(repo.repodata_path, 'repodata',
                                repo.datafiles[filetype]))
      paths.append(repo.rjoin(repo.repodata_path, repo.mdfile))
      self.io.setup_sync(repo.ljoin(repo.repodata_path, 'repodata'),
                         paths=paths, id='%s-repodata' % repo.id)
      
  def sync_repodata(self):
    backup = self.files_callback.sync_start
    self.files_callback.sync_start = lambda : None
    
    for repo in self.repos.values():
      self.log(1, L1(repo.id))
      self.io.sync_input(what='%s-repodata' % repo.id)

    self.files_callback.sync_start = backup

  def read_new_packages(self):
    for repo in self.repos.values():
      pxml = repo.rjoin(repo.repodata_path, 'repodata', repo.datafiles['primary'])
      if self.diff.handlers['input'].diffdict.has_key(pxml):
        self.log(2, L2(repo.id))
        repo.readRepoContents()
        repo.writeRepoContents(repo.pkgsfile)
      self.DATA['output'].append(repo.pkgsfile)
