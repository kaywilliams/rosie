#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
import errno
import os
import sys

from rendition import execlib

from rendition.versort import Version

from spin.constants import BOOLEANS_TRUE
from spin.logging   import L1

__all__ = ['CreateRepoMixin']

CREATEREPO_ATTEMPTS = 2

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
    if update and (path/'repodata').exists() and UPDATE_ALLOWED:
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

    count = 1
    while True:
      try:
        execlib.execute(' '.join(args))
      except execlib.ExecuteError, e:
        if count == CREATEREPO_ATTEMPTS or \
            e.errno != errno.EAGAIN or e.errno != errno.EWOULDBLOCK:
          self.log(0,
            "An unhandled exception has occurred while running 'createrepo' "
            "in the '%s' event.\n\nError message was: %s" % (self.id, e))
          sys.exit(1)
        # over here iff e.errno == EAGAIN or e.errno == EWOULDBLOCK
        count = count + 1
      else:
        break

    os.chdir(cwd)
    return repo_files

class RpmNotFoundError(IOError): pass

def RpmPackageVersion(name):
  return Version(
    execlib.execute('rpm -q --queryformat="%%{version}" %s' % name)[0])

def CommandLineVersion(name, flag='--version'):
  return Version(execlib.execute('%s %s' % (name, flag))[0])

# figure out if createrepo can accept the '--update' and '--database'
# flags
UPDATE_ALLOWED = True
DATABASE_ALLOWED = True
try:
  binary_version = CommandLineVersion('createrepo')
except (execlib.ExecuteError, IndexError), e:
  raise ImportError("missing 'createrepo' package")
else:
  if binary_version < '0.4.9':
    # can't accept '--update'
    UPDATE_ALLOWED = False
  elif binary_version == '0.4.9':
    # need to check rpm version because createrepo RPMs 0.4.9 and
    # 0.4.10, both report their createrepo version as
    # 0.4.9. Createrepo RPM 0.4.10 supports '--update'.
    try:
      if RpmPackageVersion('createrepo') < '0.4.10':
        UPDATE_ALLOWED = False
    except RpmNotFoundError:
      UPDATE_ALLOWED = False

  if binary_version < '0.4.7':
    DATABASE_ALLOWED = False
