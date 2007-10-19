"""
sources.py

downloads srpms
"""

import os
import re
import rpm
import stat

from dims import pps
from dims import shlib

from dimsbuild.constants import BOOLEANS_TRUE, SRPM_PNVRA, SRPM_REGEX
from dimsbuild.event     import Event
from dimsbuild.logging   import L0, L1, L2
from dimsbuild.validate  import InvalidConfigError

from dimsbuild.modules.shared import RepoEventMixin

P = pps.Path

API_VERSION = 5.0

SRPM_PNVRA_REGEX = re.compile(SRPM_PNVRA)

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
    self.read_config(repos='repo', files='repofiles')

  def run(self):
    self.log(0, L0("setting up input source repositories"))

    self.log(1, L1("downloading information about source packages"))
    self.sync_repodata()

    # reading primary.xml.gz files
    self.log(1, L1("reading available source packages"))
    self.read_new_packages()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()

    for repo in self.repocontainer.values():
      if not repo.pkgsfile.exists():
        raise RuntimeError("Unable to find cached file at '%s'. Perhaps you "
                           "are skipping %s before it has been allowed "
                           "to run once?" % (repo.pkgsfile, self.id))
      repo._read_repo_content(repofile=repo.pkgsfile)

    self.cvars['source-repos'] = self.repocontainer


class SourcesEvent(Event):
  "Downloads source rpms."
  def __init__(self):
    Event.__init__(self,
                   id='sources',
                   provides=['srpms', 'srpms-dir', 'publish-content'],
                   requires=['rpms', 'source-repos'])

    self.srpmdest = self.OUTPUT_DIR / 'SRPMS'
    self.DATA = {
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
    paths = []
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
                               'st_mode':  stat.S_IFREG})
          paths.append(rpmi)

    self.io.setup_sync(self.srpmdest, paths=paths, id='srpms')

  def run(self):
    self.log(0, L0("retrieving source RPMs for distribution RPMs"))

    self.log(1, L1("processing srpms"))
    self.srpmdest.mkdirs()
    self.io.sync_input(cache=True)

    # remove all obsolete SRPMs
    old_files = set(self.srpmdest.findpaths(mindepth=1, regex=SRPM_REGEX))
    new_files = set(self.io.list_output(what='srpms'))
    for obsolete_file in old_files.difference(new_files):
      obsolete_file.rm(recursive=True, force=True)

    # run createrepo
    self._createrepo()
    self.DATA['output'].extend(self.io.list_output(what=['srpms']))
    self.DATA['output'].append(self.srpmdest/'repodata')
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

  def _createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.srpmdest)
    self.log(1, L1("running createrepo"))
    shlib.execute('/usr/bin/createrepo --update -q .')
    os.chdir(pwd)


EVENTS = {'setup': [SourceReposEvent], 'ALL': [SourcesEvent]}
