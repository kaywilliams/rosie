import os
import rpm
import sys

from dims import execlib
from dims import sortlib

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

  def createrepo(self, path, groupfile=None, pretty=False,
                 update=True, quiet=True, database=True):
    "Run createrepo on the path specified."
    self.log(1, L1("running createrepo"))

    repo_files = []
    for file in self.XML_FILES:
      repo_files.append(path / file)

    args = ['/usr/bin/createrepo']
    if update and UPDATE_ALLOWED:
      args.append('--update')
    if quiet:
      args.append('--quiet')
    if groupfile:
      args.extend(['--groupfile', groupfile])
      repo_files.append(path / 'repodata'/ groupfile.basename)
    if pretty:
      args.append('--pretty')
    if database and DATABASE_ALLOWED:
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

class RpmNotFoundError(IOError): pass

def RpmPackageVersion(name):
  ts = rpm.TransactionSet()
  mi = ts.dbMatch(rpm.RPMTAG_NAME, name)
  if mi.count() == 0:
    raise RpmNotFoundError("package '%s' was not found in the RPM database" % name)
  pkg = mi.next()
  del ts
  return pkg['version']

def CommandLineVersion(name, flag='--version'):
  try:
    version = execlib.execute('%s %s' % (name, flag))[0]
  except:
    raise
  else:
    return version

# figure out if createrepo can accept the '--update' and '--database'
# flags
UPDATE_ALLOWED = True
DATABASE_ALLOWED = True
try:
  binary_version = CommandLineVersion('createrepo')
except (execlib.ExecuteError, IndexError), e:
  raise ImportError("missing 'createrepo' package")
else:
  check_version = sortlib.dcompare(binary_version, '0.4.9')
  if check_version == -1:
    # can't accept '--update'
    UPDATE_ALLOWED = False
  elif check_version == 0:
    # need to check rpm version because createrepo RPMs 0.4.9 and
    # 0.4.10, both report their createrepo version as
    # 0.4.9. Createrepo RPM 0.4.10 supports '--update'.
    try:
      rpm_version = RpmPackageVersion('createrepo')
      if sortlib.dcompare(rpm_version, '0.4.10') == -1:
        UPDATE_ALLOWED = False
    except RpmNotFoundError:
      UPDATE_ALLOWED = False

  check_version = sortlib.dcompare(binary_version, '0.4.7')
  if check_version == -1:
    # can't accept '--database' flag
    DATABASE_ALLOWED = False
