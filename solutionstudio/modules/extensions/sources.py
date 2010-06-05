#
# Copyright (c) 2010
# Solution Studio. All rights reserved.
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
"""
sources.py

downloads srpms
"""
import os
import rpm
import stat
import time

from solutionstudio.util.repo import RepoContainer, ReposFromFile, ReposFromXml
from solutionstudio.util.repo import RPM_PNVRA_REGEX

from solutionstudio.errors    import assert_file_readable, SolutionStudioError
from solutionstudio.event     import Event
from solutionstudio.logging   import L1, L2
from solutionstudio.validate  import InvalidConfigError

from solutionstudio.modules.shared import CreaterepoMixin, RepoEventMixin, SolutionStudioRepoGroup

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['SourceReposEvent', 'SourcesEvent'],
  description = 'creates a source RPMs folder',
)

class SourceReposEvent(Event, RepoEventMixin):
  "Downloads and reads the primary.xml.gz for each of the source repositories."
  def __init__(self):
    Event.__init__(self,
      id = 'source-repos',
      parentid = 'setup',
      provides = ['source-repos'],
      requires = ['input-repos']
    )

    RepoEventMixin.__init__(self)

    self.DATA = {
      'variables': [],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    updates = RepoContainer()
    if self.config.pathexists('.'):
      updates.add_repos(ReposFromXml(self.config.get('.'), cls=SolutionStudioRepoGroup))
    for filexml in self.config.xpath('repofile/text()', []):
      updates.add_repos(ReposFromFile(self.io.abspath(filexml),
                                      cls=SolutionStudioRepoGroup))

    self.setup_repos(updates)
    self.read_repodata()

  def run(self):
    self.log(1, L1("downloading information about source packages"))
    self.sync_repodata()

    # reading primary.xml.gz files
    self.log(1, L1("reading available source packages"))
    self.read_packages()

  def apply(self):
    self.io.clean_eventcache()

    for repo in self.repos.values():
      if repo.pkgsfile.exists():
        assert_file_readable(repo.pkgsfile)
        repo.repocontent.read(repo.pkgsfile)

    # set up cvars
    self.cvars['source-repos'] = self.repos

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnlessSet('source-repos')

class SourcesEvent(Event, CreaterepoMixin):
  "Downloads source rpms."
  def __init__(self):
    Event.__init__(self,
      id = 'sources',
      parentid = 'all',
      provides = ['srpms', 'srpms-dir', 'publish-content'],
      requires = ['rpms', 'source-repos']
    )
    CreaterepoMixin.__init__(self)

    self.srpmdest = self.OUTPUT_DIR / 'SRPMS'
    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'rpms\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

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
    processed_srpmset = set()
    for repo in self.cvars['source-repos'].values():
      now = time.time()
      for rpminfo in repo.repocontent.filter():
        rpmi = repo.url//rpminfo['file']
        _,n,v,r,a = self._deformat(rpmi)
        ## assuming the rpm file name to be lower-case 'rpm' suffixed
        nvra = '%s-%s-%s.%s.rpm' % (n,v,r,a)
        if nvra in srpmset:
          rpmi.stat(populate=False).update(
            st_size  = rpminfo['size'],
            st_mtime = rpminfo['mtime'],
            st_mode  = (stat.S_IFREG | 0644),
            st_atime = now)
          processed_srpmset.add(nvra)
          self.io.add_fpath(rpmi, self.srpmdest, id=repo.id)

    if srpmset != processed_srpmset:
      raise MissingSrpmsError(sorted(srpmset - processed_srpmset))

  def run(self):
    self.log(1, L1("processing srpms"))
    for repo in self.cvars['source-repos'].values():
      self.io.sync_input(cache=True, what=repo.id,
                         text=('downloading source packages - %s' % repo.id))

    # remove all obsolete SRPMs
    old_files = set(self.srpmdest.findpaths(mindepth=1, regex='.*\.src\.rpm'))
    new_files = set(self.io.list_output())
    for obsolete_file in (old_files - new_files):
      obsolete_file.rm(recursive=True, force=True)

    # run createrepo
    repo_files = self.createrepo(self.srpmdest)
    self.DATA['output'].extend(repo_files)

    self.DATA['output'].extend(self.io.list_output(what=['srpms']))

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['srpms'] = self.io.list_output(what='srpms')
    self.cvars['srpms-dir'] = self.srpmdest
    try: self.cvars['publish-content'].add(self.srpmdest)
    except: pass

  def _deformat(self, srpm):
    try:
      return RPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.log(4, L2("DEBUG: Unable to extract srpm information from name '%s'" % srpm))
      return (None, None, None, None, None)

  def error(self, e):
    # performing a subset of Event.error since sync handles partially downloaded files
    if self.mdfile.exists():
      debugdir = (self.mddir + '.debug')
      debugdir.mkdir()
      self.mdfile.rename(debugdir/self.mdfile.basename)


class MissingSrpmsError(SolutionStudioError):
  message = "The following SRPMs were not found in any input repo:\n%(srpms)s"
