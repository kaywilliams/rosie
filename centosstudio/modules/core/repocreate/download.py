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
import stat
import time
import rpmUtils
import yum

from rpmUtils.arch import getArchList

from centosstudio.callback  import CachedSyncCallback

from centosstudio.util.repo import RPM_PNVRA_REGEX

from centosstudio.errors    import (CentOSStudioEventError, CentOSStudioIOError,
                                    assert_file_has_content)
from centosstudio.event     import Event
from centosstudio.cslogging import L1, L2

from centosstudio.modules.shared import RepomdMixin

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['DownloadEvent'],
    description = 'downloads package list RPMs',
    group       = 'repocreate',
  )

class DownloadEvent(RepomdMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'download',
      version = 1.01,
      parentid = 'repocreate',
      ptr = ptr,
      provides = ['os-content', 'repomd-file', 'treeinfo-checksums'],
      requires = ['pkglist', 'repos'],
      conditionally_requires = ['gpgcheck-enabled', 'gpgkeys', 'groupfile'],
    )

    self._validarchs = getArchList(self.arch)

    self.DATA = {
      'variables': ['packagepath', 'cvars[\'pkglist\']'],
      'input':     [],
      'output':    [],
    }

    RepomdMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)
    self.rpmsdir = self.REPO_STORE//self.packagepath
    self.DATA['variables'].append('rpmsdir')

    # get list of repos to skip downloading from
    skip = [ r.get('text()') for r in self.config.xpath('skip-repo', []) ]
    if self.type != 'system': skip.extend(['base', 'updates'])

    # setup for downloads
    for repo in self.cvars['repos'].values():
      if repo.id in skip: continue
      for subrepo in repo.subrepos.values():
        now = time.time()
        # populate rpm time and size from repodata values (for performance)
        if subrepo.id not in self.cvars['pkglist']:
          continue
        for tup in self.cvars['pkglist'][subrepo.id]: 
          _, _, path, size, mtime = tup
          rpm = subrepo.url//path
          rpm.stat(populate=False).update(
            st_size  = size,
            st_mtime = mtime,
            st_mode  = (stat.S_IFREG | 0644),
            st_atime = now)
          # add rpm for io sync
          self.io.add_fpath(rpm, self.rpmsdir, id=subrepo.id)

    # setup for gpgchecking
    self.rpmdb_dir = self.mddir / 'gpgcheck'
    if getattr(self, 'cvars[\'gpgcheck-enabled\']', True):
      self.DATA['variables'].append('cvars[\'gpgcheck-enabled\']')
      if self.cvars['gpgkeys']:
        self.DATA['input'].extend(self.cvars['gpgkeys'])

    # setup for createrepo
    if self.cvars['groupfile']:
      self.DATA['input'].append(self.cvars['groupfile'])

  def run(self):
    self._process_keys()
    try:
      self._process_packages()
    finally:
      self._cleanup()

    # run createrepo
    repo_files = self.createrepo(self.rpmsdir,
                                 groupfile=self.cvars['groupfile'],
                                 checksum=self.locals.L_CHECKSUM['type'])
    self.DATA['output'].extend(repo_files)

  def apply(self):
    self.cvars['repomd-file'] = self.rpmsdir / 'repodata/repomd.xml'
    self.cvars.setdefault('treeinfo-checksums', set()).add(
      (self.rpmsdir, 'repodata/repomd.xml'))

  def verify_repodata_directory(self):
    self.verifier.failUnlessExists(self.cvars['repomd-file'])

  def error(self, e):
    # performing a subset of Event.error since sync handles partially 
    # downloaded files
    if self.mdfile.exists():
      debugdir=(self.mddir + '.debug')
      debugdir.mkdir()
      self.mdfile.rename(debugdir / self.mdfile.basename)

  def _process_keys(self):
    if not self.cvars['gpgcheck-enabled']:
      self.rpmdb_dir.rm(force=True, recursive=True)
      self.ts=None
      return

    # if any prior key ids no longer exist, start clean to force rechecking
    clean = False
    if 'cvars[\'gpgkey-ids\']' in self.diff.variables.difference():
      md, curr = self.diff.variables.difference()['cvars[\'gpgkey-ids\']']
      if md and not curr: #prior key has been removed
        clean = True
    if clean:
      self.log(1, L1("gpgkeys removed - rechecking all packages"))
      self.io.clean_eventcache(all=true)

    # create rpmdb for key storage
    self.ts = rpmUtils.transaction.TransactionWrapper(root=self.rpmdb_dir)

    #add keys to rpmdb
    for key in self.cvars['gpgkeys']:
      #validate key
      assert_file_has_content(key, cls=GpgkeyIOError)

      #add to rpmdb
      self.ts.pgpImportPubkey(yum.misc.procgpgkey(key.read_text()))

  def _process_packages(self):
    for subrepo in self.cvars['pkglist']:
      cb = DownloadCallback(self.logger, self.mddir, self.ts, subrepo)
      self.io.process_files(link=True, cache=True, what=subrepo, callback=cb,
                         text=("downloading packages - '%s'" % subrepo))

  def _cleanup(self):
    if self.ts:
      self.ts.close()

#------ CALLBACK ------#
class DownloadCallback(CachedSyncCallback):
  """
  Extends the CachedSyncCallback to provide gpgkey checking for downloaded 
  packages.
  """
  error_text = { 1 : 'missing gpgkey',
                 2 : 'error reading package signature',
                 3 : 'untrusted gpgkey',
                 4 : 'unsigned package'}

  def __init__(self, logger, relpath, ts, repoid):
    CachedSyncCallback.__init__(self, logger, relpath)
    self.ts = ts #rpm transaction
    self.repo = repoid

  def start(self, src, dest):
    self.pkg = dest # store pkg so we can check it in _cache_end method
    CachedSyncCallback.start(self, src, dest)

  def _cache_end(self):
    if self.ts:
      r = rpmUtils.miscutils.checkSig(self.ts, self.pkg)
      if r != 0: # check failed
        raise RpmSignatureInvalidError(pkg=self.pkg.basename, repo=self.repo,
                                       error=self.error_text[r])
    CachedSyncCallback._cache_end(self)
   

#------ ERRORS ------#
class RpmsNotFoundError(CentOSStudioEventError):
  message = "The following RPMs were not found in any input repos:\n%(rpms)s"

class RpmSignatureInvalidError(CentOSStudioEventError):
  message = ("The '%(pkg)s' package from the '%(repo)s' repository failed GPG "
             "key check. The error was '%(error)s'. You may need to list "
             "additional gpgkeys in your repo definition(s).")

class GpgkeyIOError(CentOSStudioIOError):
  message = "Cannot read gpgkey '%(file)s': [errno %(errno)d] %(message)s"
