import os
import sys

from dims import listcompare
from dims import pps
from dims import shlib

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
    self.repocontainer = RepoContainer()

  def read_config(self, repos=None, files=None):
    # one or the other of repos or files is required by validation
    if repos:
      for repoxml in self.config.xpath(repos, []):
        id = repoxml.get('@id')
        self.repocontainer.add_repo(id)
        repo = self.repocontainer[id]
        repo.read_config(repoxml)
        repo.repodata = repoxml.get('repodata-path/text()', '')

    if files:
      for filexml in self.config.xpath(files, []):
        self.repocontainer.read(filexml.text)

    for repo in self.repocontainer.values():
      repo.localurl = self.mddir/repo.id
      repo.pkgsfile = self.mddir/repo.id/'packages'

      repo._read_repodata()

      paths = []
      for filetype in repo.datafiles.keys():
        paths.append(repo.remoteurl / \
                     repo.repodata / \
                     'repodata' / \
                     repo.datafiles[filetype])
      paths.append(repo.remoteurl/repo.repodata/repo.mdfile)
      self.io.setup_sync(repo.localurl/repo.repodata/'repodata',
                         paths=paths, id='%s-repodata' % repo.id)

    self.repoids = self.repocontainer.keys()
    self.DATA['variables'].append('repoids')

  def sync_repodata(self):
    for repo in self.repocontainer.values():
      self.log(1, L1(repo.id))
      self.io.sync_input(what='%s-repodata' % repo.id, cache=True, cb=None)

  def read_new_packages(self):
    for repo in self.repocontainer.values():
      pxml = repo.remoteurl/repo.repodata/'repodata'/repo.datafiles['primary']
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

class CreateRepoMixin:
  def __init__(self):
    pass

  def createrepo(self, path, groupfile=None, pretty=False, update=True, quiet=True):
    "Run createrepo on the path specified."
    self.log(1, L1("running createrepo"))

    args = ['/usr/bin/createrepo']
    if update:
      args.append('--update')
    if quiet:
      args.append('--quiet')
    if groupfile:
      args.extend(['--groupfile', groupfile])
    if pretty:
      args.append('--pretty')
    if self.config.get('@database', 'false') in BOOLEANS_TRUE:
      args.append('--database')
    else:
      ## HACK: if not creating sqlite files, delete existing ones (if
      ## they exist)
      for bz2 in path.findpaths(glob='*.sqlite.bz2'):
        bz2.rm()
    args.append('.')

    cwd = os.getcwd()
    os.chdir(path)
    try:
      shlib.execute(' '.join(args))
    except shlib.ShExecError, e:
      self.log(0,
        "An unhandled exception has occurred while running 'createrepo'. "
        "in the '%s' event. If the version of createrepo installed on your "
        "machine is < 0.4.7, then you cannot set the 'database' attribute "
        "to be 'True' in the config file. \n\nError message was: %s" % (self.id, e))
      sys.exit(1)
    os.chdir(cwd)

