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

from rendition import shlib

from rendition.versort import Version

from spin.logging   import L1

__all__ = ['CreaterepoMixin']

CREATEREPO_ATTEMPTS = 2

class CreaterepoMixin:
  def __init__(self):
    self.cvars['createrepo-version'] = Version(
      shlib.execute('rpm -q --queryformat="%{version}" createrepo')[0])

  def createrepo(self, path, groupfile=None, pretty=False,
                 update=True, quiet=True, database=True):
    "Run createrepo on the path specified."
    self.log(1, L1("running createrepo"))

    repo_files = []
    for file in self.locals.L_CREATEREPO['xml-files'].keys():
      repo_files.append(path / file)

    args = ['/usr/bin/createrepo']
    if update and (path/'repodata').exists() and \
       self.locals.L_CREATEREPO['capabilities']['update']:
      args.append('--update')
    if quiet:
      args.append('--quiet')
    if groupfile:
      args.extend(['--groupfile', groupfile])
      repo_files.append(path / 'repodata'/ groupfile.basename)
    if pretty:
      args.append('--pretty')
    if database and \
       self.locals.L_CREATEREPO['capabilities']['database']:
      args.append('--database')
      for file in self.locals.L_CREATEREPO['sqlite-files'].keys():
        repo_files.append(path / file)
    args.append('.')

    cwd = os.getcwd()
    os.chdir(path)

    count = 0
    while True:
      try:
        shlib.execute(' '.join(args))
      except shlib.ShExecError, e:
        if count >= CREATEREPO_ATTEMPTS or \
            e.errno not in [errno.EAGAIN, errno.EWOULDBLOCK]:
          raise
        count += 1
      else:
        break

    os.chdir(cwd)
    return repo_files

def RpmPackageVersion(name):
  return Version(
    shlib.execute('rpm -q --queryformat="%%{version}" %s' % name)[0])
