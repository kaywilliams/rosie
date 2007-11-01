import os
import sys

from dims import execlib

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.logging   import L1

__all__ = ['CreateRepoMixin']

class CreateRepoMixin:

  # For now the list of files are hardcoded in the following two
  # lists. If in the future, the names of the files changes, we can
  # move them to a local dictionary.
  XML_FILES = ['repodata/filelists.xml.gz',
               'repodata/other.xml.gz',
               'repodata/primary.xml.gz',
               'repodata/repomd.xml']
  SQLITE_FILES = ['repodata/filelists.sqlite.bz2',
                  'repodata/other.sqlite.bz2',
                  'repodata/primary.sqlite.bz2']
  def __init__(self):
    pass

  def createrepo(self, path, groupfile=None, pretty=False, update=True, quiet=True):
    "Run createrepo on the path specified."
    self.log(1, L1("running createrepo"))

    repo_files = []
    for file in self.XML_FILES:
      repo_files.append(path / file)

    args = ['/usr/bin/createrepo']
    if update:
      args.append('--update')
    if quiet:
      args.append('--quiet')
    if groupfile:
      args.extend(['--groupfile', groupfile])
      repo_files.append(path / 'repodata'/ groupfile.basename)
    if pretty:
      args.append('--pretty')
    if self.config.get('@database', 'false') in BOOLEANS_TRUE:
      args.append('--database')
      for file in self.SQLITE_FILES:
        repo_files.append(path / file)
    args.append('.')

    cwd = os.getcwd()
    os.chdir(path)
    try:
      execlib.execute(' '.join(args))
    except execlib.ExecuteError, e:
      self.log(0,
        "An unhandled exception has occurred while running 'createrepo' "
        "in the '%s' event. If the version of createrepo installed on your "
        "machine is < 0.4.7, then you cannot set the 'database' attribute "
        "to be 'True' in the config file. \n\nError message was: %s" % (self.id, e))
      sys.exit(1)
    os.chdir(cwd)
    return repo_files
