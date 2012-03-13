#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

from centosstudio.util import shlib

from centosstudio.util.versort import Version

from centosstudio.callback import TimerCallback
from centosstudio.cslogging  import L1

__all__ = ['RepomdMixin']

CREATEREPO_ATTEMPTS = 2

class RepomdMixin:
  repomd_mixin_version = "1.00"

  def __init__(self, *args, **kwargs):
    self.cvars['createrepo-version'] = Version(
      shlib.execute('createrepo --version')[0].lstrip("createrepo "))
    if self.logger:
      self.crcb = TimerCallback(self.logger)
    else:
      self.crcb = None

    self.DATA['variables'].append('repomd_mixin_version')

  def createrepo(self, path, groupfile=None, pretty=False,
                 update=True, quiet=True, database=True, checksum=None):
    "Run createrepo on the path specified."
    if self.crcb: self.crcb.start("running createrepo")

    repo_files = []
    for file in self.locals.L_CREATEREPO['xml-files'].keys():
      repo_files.append(path / file)

    args = ['/usr/bin/createrepo']
    #note: using createrepo help to determine update capability since 
    #createrepo reported version number was incorrect (0.4.9) for version
    #0.4.11.
    if (update and (path/'repodata').exists() and 
       '--update' in ' '.join(shlib.execute('createrepo --help'))):
      args.append('--update')
    if quiet:
      args.append('--quiet')
    if groupfile:
      args.extend(['--groupfile', groupfile])
      repo_files.append(path / 'repodata'/ groupfile.basename)
      if self.locals.L_CREATEREPO['capabilities']['gzipped_groupfile']:
        repo_files.append(path / 'repodata/%s.gz' % groupfile.basename)
    if pretty:
      args.append('--pretty')
    if (database and 
       self.locals.L_CREATEREPO['capabilities']['database']):
      args.append('--database')
      for file in self.locals.L_CREATEREPO['sqlite-files'].keys():
        repo_files.append(path / file)
    if (checksum and 
       'checksum' in self.locals.L_CREATEREPO['capabilities']):
      args.append('--checksum %s' % checksum)
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
    if self.crcb: self.crcb.end()
    return repo_files

