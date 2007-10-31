from dims import pps

from dimsbuild.logging   import L1, L2
from dimsbuild.repo      import RepoContainer

__all__ = ['RepoEventMixin']

class RepoEventMixin:
  def __init__(self):
    self.repocontainer = RepoContainer()

  def read_config(self, repos=None, files=None):
    # one or the other of repos or files is required by validation
    if repos:
      for repoxml in self.config.xpath(repos, []):
        id = repoxml.get('@id')
        self.repocontainer.add_repo(id)
        self.repocontainer[id].read_config(repoxml)

    if files:
      for filexml in self.config.xpath(files, []):
        self.repocontainer.read(filexml.text)

    for repo in self.repocontainer.values():
      repo.localurl = self.mddir/repo.id
      repo.pkgsfile = self.mddir/repo.id/'packages'

      if repo.id == self.cvars['base-repoid']:
        folder = 'images'
        args = {'glob': folder,
                'type': pps.constants.TYPE_DIR,
                'mindepth': 1,
                'maxdepth': 1}
        if repo.remoteurl.findpaths(**args):
          repo.osdir = repo.remoteurl
        elif repo.remoteurl.dirname.findpaths(**args):
          repo.osdir = repo.remoteurl.dirname
        else:
          raise RuntimeError("Unable to find a folder named '%s' at '%s' "
          "or '%s'. Check the baseurl for the '%s' repo, or specify an alternative "
          "base-repo, and try again."
          % (folder, repo.remoteurl, repo.remoteurl.dirname, repo.id))

      repo._read_repodata()

      paths = []
      for filetype in repo.datafiles.keys():
        paths.append(repo.remoteurl / \
                     'repodata' / \
                     repo.datafiles[filetype])
      paths.append(repo.remoteurl/repo.mdfile)
      self.io.setup_sync(repo.localurl/'repodata',
                         paths=paths, id='%s-repodata' % repo.id)

    self.repoids = self.repocontainer.keys()
    self.DATA['variables'].append('repoids')

  def sync_repodata(self):
    for repo in self.repocontainer.values():
      self.log(1, L1(repo.id))
      self.io.sync_input(what='%s-repodata' % repo.id, cache=True, cb=None)

  def read_new_packages(self):
    for repo in self.repocontainer.values():
      pxml = repo.remoteurl/'repodata'/repo.datafiles['primary']
      # determine if the repo has a new id
      newid = False
      if self.diff.handlers['variables'].diffdict.has_key('repoids'):
        old,new = self.diff.handlers['variables'].diffdict['repoids']
        if not hasattr(old, '__iter__'): old = []
        newid = repo.id in set(new).difference(set(old))
      if self.diff.handlers['input'].diffdict.has_key(pxml) or newid:
        self.log(2, L2(repo.id))
        repo._read_repo_content()
        repo.write_repo_content(repo.pkgsfile)
      self.DATA['output'].append(repo.pkgsfile)
