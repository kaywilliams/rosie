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
"""
sources.py

downloads srpms
"""
import os
import rpm
import stat

from rendition import pps

from spin.constants import SRPM_PNVRA_REGEX, SRPM_REGEX
from spin.event     import Event
from spin.logging   import L1, L2
from spin.validate  import InvalidConfigError

from spin.modules.shared import CreateRepoMixin, RepoEventMixin

P = pps.Path

API_VERSION = 5.0
EVENTS = {'setup': ['SourceReposEvent'], 'all': ['SourcesEvent']}

class SourceReposEvent(Event, RepoEventMixin):
  "Downloads and reads the primary.xml.gz for each of the source repositories."
  def __init__(self):
    Event.__init__(self,
                   id='source-repos',
                   provides=['source-repos'])
    RepoEventMixin.__init__(self)

    self.DATA = {
      'variables': [],
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def validate(self):
    if self.config.get('repo', None) is None and \
       self.config.get('repofile', None) is None:
      raise InvalidConfigError(self.config,
         "Config file must specify at least one 'repo' element or "
         "at least one 'repofile' element as a child to the 'sources' "
         "element.")

  def setup(self):
    self.diff.setup(self.DATA)
    self.read_config(repos='repo', files='repofile')

  def run(self):
    self.log(1, L1("downloading information about source packages"))
    self.sync_repodata()

    # reading primary.xml.gz files
    self.log(1, L1("reading available source packages"))
    self.read_new_packages()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

    for repo in self.repocontainer.values():
      try: # hack, errors caught by validator
        repo._read_repo_content(repofile=repo.pkgsfile)
      except:
        continue

    self.cvars['source-repos'] = self.repocontainer

  def verify_pkgsfiles_exist(self):
    "verify all pkgsfiles exist"
    for repo in self.repocontainer.values():
      self.verifier.failUnlessExists(repo.pkgsfile)

  def verify_repodata(self):
    "verify repodata exists"
    for repo in self.repocontainer.values():
      self.verifier.failUnlessExists(repo.localurl / repo.mdfile)
      self.verifier.failUnlessExists(repo.localurl /
                                     'repodata' /
                                     repo.datafiles['primary'])

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnless(self.cvars['source-repos'])


class SourcesEvent(Event, CreateRepoMixin):
  "Downloads source rpms."
  def __init__(self):
    Event.__init__(self,
                   id='sources',
                   provides=['srpms', 'srpms-dir', 'publish-content'],
                   requires=['rpms', 'source-repos'])
    CreateRepoMixin.__init__(self)

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
    for repo in self.cvars['source-repos'].values():
      for rpminfo in repo.repoinfo:
        rpmi = rpminfo['file']
        _,n,v,r,a = self._deformat(rpmi)
        ## assuming the rpm file name to be lower-case 'rpm' suffixed
        nvra = '%s-%s-%s.%s.rpm' %(n,v,r,a)
        if nvra in srpmset:
          rpmi = P(rpminfo['file'])
          if isinstance(rpmi, pps.path.http.HttpPath): #! bad
            rpmi._update_stat({'st_size':  rpminfo['size'],
                               'st_mtime': rpminfo['mtime'],
                               'st_mode':  (stat.S_IFREG | 0644)})
          self.io.add_fpath(rpmi, self.srpmdest, id='srpms')

  def run(self):
    self.log(1, L1("processing srpms"))
    self.srpmdest.mkdirs()
    self.io.sync_input(cache=True)

    # remove all obsolete SRPMs
    old_files = set(self.srpmdest.findpaths(mindepth=1, regex=SRPM_REGEX))
    new_files = set(self.io.list_output(what='srpms'))
    for obsolete_file in old_files.difference(new_files):
      obsolete_file.rm(recursive=True, force=True)

    # run createrepo
    repo_files = self.createrepo(self.srpmdest)
    self.DATA['output'].extend(repo_files)

    self.DATA['output'].extend(self.io.list_output(what=['srpms']))
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['srpms'] = self.io.list_output(what='srpms')
    self.cvars['srpms-dir'] = self.srpmdest
    try: self.cvars['publish-content'].add(self.srpmdest)
    except: pass

  def _deformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.log(4, L2("DEBUG: Unable to extract srpm information from name '%s'" % srpm))
      return (None, None, None, None, None)
