#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

import copy
import errno
import fnmatch
import os
import re
import time

from deploy.event import Event

from deploy.util import listfmt
from deploy.util import pps
from deploy.util import rxml

from deploy.util.difftest.filesdiff import DiffTuple

from deploy.util.pps.constants import TYPE_DIR

from deploy.errors    import (DeployEventError,
                                    DeployIOError, RhnSupportError,
                                    assert_file_readable, 
                                    assert_file_has_content)
from deploy.dlogging    import L1, L2
from deploy.constants    import BOOLEANS_TRUE, BOOLEANS_FALSE
from deploy.errors       import DuplicateIdsError
from deploy.event.fileio import InputFileError
from deploy.validate     import InvalidConfigError

from deploy.util.repo          import (ReposFromXml, ReposFromFile, 
                                       getDefaultRepos, RepoDuplicateIdsError)
from deploy.util.repo.repo     import (YumRepo, RepoContainer, NSMAP, 
                                             InvalidFileError)
from deploy.util.repo.defaults import TYPE_ALL

__all__ = ['RepoSetupEventMixin', 'RepoEventMixin', 'DeployRepo', 
           'DeployRepoGroup', 'DeployRepoFileParseError']

# list of folders that don't contain repodata folders for sure
NOT_REPO_GLOB = ['images', 'isolinux', 'repodata', 'repoview',
                 'stylesheet-images']

class DeployRepo(YumRepo):
  keyfilter = ['id', 'systemid']
  treeinfofile = pps.path('.treeinfo')

  def __init__(self, **kwargs):
    YumRepo.__init__(self, **kwargs)
    self.localurl = None
    self._systemid = None # system id, for redhat mirrors

  def _boolparse(self, s):
    if s.lower() in BOOLEANS_FALSE:
      return False
    elif s.lower() in BOOLEANS_TRUE:
      return True
    elif s is None:
      return None
    else:
      raise ValueError("invalid boolean value '%s'" % s)

  @property
  def download(self):
    if self.id in ['base', 'updates']:
      default = 'false'
    else:
      default = 'true'
    return self._boolparse(self.get('download', default))

  def get_rpm_version(self, names):
    # filter list of names if necessary
    names = [ n for n in names if self.repocontent.has_package(n) ]
    if not names: return (None, None)

    scan = re.compile('(?:.*/)?(' + '|'.join(names) + ')-(.*)(\..*\..*$)')
    assert_file_readable(self.pkgsfile, PkgsfileIOError,
                         names=listfmt.format(names,
                                              sep=', ', pre='\'',
                                              post='\'', last=' or '))
    for rpm in self.pkgsfile.read_lines():
      match = scan.match(rpm)
      if match:
        try:
          return match.groups()[0:2]
        except (AttributeError, IndexError):
          pass
    return (None, None)

  def _xform_uri(self, p):
    p = pps.path(p)
    try:
      if isinstance(p, pps.Path.rhn.RhnPath):
        systemid = self.get('systemid')
        if systemid:
          systemid = pps.path(systemid).realpath()
          try:
            assert_file_has_content(systemid, cls=SystemidIOError, repoid=self.id)
          except pps.lib.rhn.SystemidInvalidError, e:
            raise SystemidInvalidError(systemid, self.id, str(e))
          p.systemid = systemid
        else:
          raise SystemidUndefinedError(self.id)
      else:
        p = YumRepo._xform_uri(self, p)
    except AttributeError:
      p = YumRepo._xform_uri(self, p)
    return p

class RhnDeployRepo(DeployRepo):
  # redhat's RHN repos are very annoying in that they have inconsitent
  # metadata at times.  This class aims to account for this instability

  EMPTY_FILE_CSUM = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
  MAX_TRIES = 10 # number of times to try redownloading repomd

  def read_repomd(self):
    i = 0; consistent = False
    while i < self.MAX_TRIES:
      DeployRepo.read_repomd(self)
      if self.EMPTY_FILE_CSUM not in \
        self.repomd.xpath('//repo:data/repo:checksum/text()',
                          namespaces=NSMAP):
        consistent = True; break
      i += 1
    if not consistent:
      raise InconsistentRepodataError(self.id, self.MAX_TRIES)


class DeployRepoGroup(DeployRepo):
  def __init__(self, **kwargs):
    DeployRepo.__init__(self, **kwargs)

    self._repos = None
    self.has_installer_files = False

  def _populate_repos(self):
    "Find all the repos we contain and classify ourself"
    self._repos = RepoContainer()

    # check validity of mirrorlist
    try:
      self.url # prepopulates url's mirrorgroup cache, raises below error
    except pps.lib.mirror.MirrorlistFormatInvalidError, e:
      raise MirrorlistFormatInvalidError(self.id, e.lineno, e.line, e.reason)

    # need special handling for rhn paths
    cls = DeployRepo
    try:
      if isinstance(self.url.realm, pps.Path.rhn.RhnPath):
        cls = RhnDeployRepo
    except AttributeError:
      if ( self.url.realm.scheme == 'rhn' or
           self.url.realm.scheme == 'rhns' ):
        raise RhnSupportError()

    # first make sure we can access the repomdfile location (e.g. no network or
    # permissions errors)
    try:
      (self.url/self.repomdfile).stat()
    except pps.Path.error.PathError, e:
      if e.errno != errno.ENOENT: # report errors other than "does not exist"
        raise InputFileError(errno=e.errno, message=e.strerror, 
                             file=self.url.realm/self.repomdfile) 

    # get directory listing so we can figure out information about this repo
    # find all subrepos
    repos = []

    if (self.url/self.repomdfile).exists():
      updates = {}
      for k,v in self.items():
        if k not in ['id']:
          updates[k] = v
      R = cls(id=self.id, **updates)
      R._relpath = pps.path('.')
      try:
        self._repos.add_repo(R)
      except RepoDuplicateIdsError, e:
        raise DuplicateIdsError('repo', e.id)

    else:
      for d in self.url.findpaths(type=TYPE_DIR, mindepth=1, maxdepth=1,
                                  nglob=NOT_REPO_GLOB):
        if (d/self.repomdfile).exists():
          updates = {}
          for k,v in self.items():
            if k not in ['id', 'mirrorlist', 'baseurl']:
              updates[k] = v
          # it doesn't make sense for a subrepo to have a mirrorlist; however,
          # we can fake it by converting all the mirror items into a baseurl
          # list!
          updates['baseurl'] = \
            '\n'.join([ x/d.basename for x,e in self.url.mirrorgroup if e ])
          R = cls(id='%s-%s' % (self.id, d.basename), **updates)
          R._relpath = d.basename
          try:
            self._repos.add_repo(R)
          except RepoDuplicateIdsError, e:
            raise DuplicateIdsError('repo', e.id)

    if len(self._repos) == 0:
      raise RepodataNotFoundError(self.id, self.url.realm)

    # set up $yumvar replacement for all subrepos
    for R in self._repos.values():
      R.vars = self.vars

    # classify this repo - does it have installer files?
    if (self.url/'images').exists() and (self.url/'isolinux').exists():
      self.has_installer_files = True


  def __str__(self):
    return self.tostring(pretty=True)

  def tostring(self, **kwargs):
    return self.subrepos.tostring(**kwargs)

  def lines(self, **kwargs):
    baseurls = [ pps.path(x) for x in (kwargs.get('baseurl') or '').split() ]
    l = []
    for repo in self.subrepos.values():
      if baseurls:
        kwargs['baseurl'] = '\n'.join([ b/repo._relpath for b in baseurls ])
      l.extend(repo.lines(**kwargs))
      l.append('')
    return l

  def read_repomd(self):
    for subrepo in self.subrepos.values():
      subrepo.read_repomd()
      for k,v in subrepo.datafiles.items():
        new = copy.copy(v)
        new.href = subrepo._relpath/v.href
        self.datafiles.setdefault(k, []).append(new)

  @property
  def subrepos(self):
    if not self._repos:
      self._populate_repos()
    return self._repos

class RepoSetupEventMixin(Event):
  """Uses ReposFromXml to add repos to the repos cvar. Creates repos cvar if
     it does not exist"""
  def __init__(self):
    self.provides = set(['repos'])

  def apply(self):
    if self.config.xpath('repo', []):
      try:
        (self.cvars.setdefault('repos', RepoContainer()).
                               add_repos(ReposFromXml(self.config.getxpath('.'),
                               cls=DeployRepoGroup)))
      except RepoDuplicateIdsError, e:
        raise DuplicateIdsError('repo', e.id)


class RepoEventMixin(Event):
  def __init__(self, *args, **kwargs):
    self.repos = RepoContainer()

  def validate(self):
    # if mode == system, repos config must contain at least one repo or repofile
    if self.type == "system" and (not self.config.xpath('repo', []) and 
                                  not self.config.xpath('repofile', [])):
      raise InvalidConfigError(self._config.file,
        "The <%s> element must contain at least one <repo> or <repofile> " 
        "element when building a system repo." % self.id)

  def setup_repos(self, repos=None):
    """
    Populates self.repos with Repo objects from the specified defaults
    combined with any desired updates.  Doesn't include repos that are
    disabled.  Handles setting up self.DATA['variables'] for repoids.
    Returns the created RepoContainer (self.repos).

    This method should typically be called in Event.setup()

    repos : a RepoContainer or dictionary containing Repos to use
    """

    self.log(4, L1("adding repos"))
    for id,R in repos.items():
      self.log(4, L2(id))
      try:
        self.repos.add_repo(R)
      except RepoDuplicateIdsError, e:
        raise DuplicateIdsError('repo', e.id)

    for repo in self.repos.values():
      # remove disabled repos
      if not repo.enabled:
        self.log(5, L1("Removing disabled repo '%s'" % repo.id))
        del self.repos[repo.id]
        continue

      # set $yumvars
      repo.vars['$releasever'] = self.config.getxpath(
                                 'releasever/text()', self.version)
      repo.vars['$basearch']   = self.arch
      
      # extend gpgkey to include keys from gpgkey.list
      listfile = repo.url.realm / 'gpgkeys/gpgkey.list'
      if listfile.exists():
        lines = listfile.read_lines()
        if lines[0].startswith("RPM-GPG-KEY"):
          repo.extend_gpgkey(['%s/gpgkeys/%s' % (repo.url.realm, x) 
                              for x in lines])

    # make sure we got at least one repo out of that mess
    if self.type == "system" and not len(self.repos) > 0:
      raise NoReposEnabledError(self.id)

    # warn if multiple repos use the same mirrorlist and different baseurls
    mirrorgroups = {}
    for repo in self.repos.values():
      if not repo.mirrorlist: continue
      ( mirrorgroups.setdefault(repo.mirrorlist, {})
                    .setdefault(tuple(repo.baseurl), [])
                    .append(repo.id) )
    for mg,baseurls in mirrorgroups.items():
      if len(baseurls.keys()) > 1:
        r = []
        for baseurl in baseurls.values():
          r.extend(baseurl)
        self.log(1, "Warning: the repos %s use the same mirrorlist, "
          "'%s', but have different baseurls; this can result in"
          "unexpected behavior." % (r, mg))

    self.repoids = self.repos.keys()
    self.DATA['variables'].append('repoids')

    return self.repos

  def read_repodata(self):
    """
    Reads repository metadata and sets up the necessary IO data structures
    so that repodata can be synced with .sync_repodata(), below.  Sets
    up each repo's .datafiles dictionary, populates self.DATA['input']
    and self.DATA['output'] with these files, and sets .localurl.

    This method should typically be called in Event.setup(), after
    .setup_repos().  It is only necessary to call this if you want to use
    .sync_repodata(), below, to copy down all repository metadata.
    """

    # set the DiffTuple type to ReposDiffTuple to handle the case when repodata
    # mtimes are -1
    self.diff.input.tupcls = ReposDiffTuple

    self.log(4, L1("reading repository metadata"))
    for repo in self.repos.values():
      self.log(4, L2(repo.id))
      # set localurl
      repo.localurl = self.mddir/repo.id
      # read metadata
      try:
        repo.read_repomd()
      except InvalidFileError, e:
        raise InvalidRepomdFileError(message=e)

      # add .treeinfo to io sync
      src = repo.url/repo.treeinfofile
      dst = self.mddir/repo.id
      if src.exists():
        self.io.add_fpath(src, dst, id='%s-repodata' % repo.id)

      # add datafiles to io sync
      for subrepo in repo.subrepos.values():

        for datafile in subrepo.iterdatafiles():
          src = subrepo.url/datafile.href
          csh = (self.cache_handler.cache_dir /
                 self.cache_handler._gen_hash(src))
          dst = self.mddir/repo.id/subrepo._relpath/datafile.href

          existing = None
          if   dst.exists(): existing = dst
          elif csh.exists(): existing = csh

          # if checksums are the same, file hasn't changed; update server's
          # mtime to account for this
          if existing and datafile.checksum == existing.checksum(
            type=datafile.checksum_type):
            mtime = existing.stat().st_mtime
          else:
            mtime = float(datafile.timestamp)

          src.stat().update(st_mtime=mtime)

          self.io.add_fpath(src, dst.dirname, id='%s-repodata' % repo.id)

  def sync_repodata(self):
    """
    Synchronizes repository metadata from the primary location to a local
    cache.

    This method should typically be called in Event.run(); it must be
    preceded by a call to .read_repodata(), above.
    """

    for repo in self.repos.values():
      # explicitly create directory for repos that don't have repodata
      (self.mddir/repo.id).mkdirs()

      # always write repomd.xml since rhn doesn't give us timestamps
      for subrepo in repo.subrepos.values():
        src = subrepo.url/subrepo.repomdfile
        dst = self.mddir/repo.id/subrepo._relpath/subrepo.repomdfile
        (dst.dirname).mkdirs()
        src.cp(dst.dirname)
        self.DATA['output'].append(dst)

      # sync repo datafiles and treeinfo
      self.io.process_files(what='%s-repodata' % repo.id, cache=True,
                         text="downloading repodata - '%s'" % repo.id)

    # verify synced data via checksums
    self.logger.log(3, L1("verifying repodata file checksums"))
    for repo in self.repos.values():
      for subrepo in repo.subrepos.values():
        for datafile in subrepo.iterdatafiles():
          f = self.mddir/repo.id/subrepo._relpath/datafile.href
          f.uncache('checksum') # uncache previously-cached shasum
          got = f.checksum(type=datafile.checksum_type)
          if datafile.checksum != got:
            raise RepomdCsumMismatchError(datafile.href.basename,
                                          repoid=repo.id,
                                          got=got,
                                          expected=datafile.checksum)

class ReposDiffTuple(DiffTuple):
  attrib = DiffTuple.attrib + [('csum', str)]

  def __init__(self, path=None):
    DiffTuple.__init__(self, path)

    self.csum = None

    if self.mtime == -1:
      # if mtime is -1, the path must exist, so we don't need try/except
      self.csum = self.path.checksum()


class NoReposEnabledError(DeployEventError, RuntimeError):
  message = "No enabled repos in '%(modid)s' module"

class RepodataNotFoundError(DeployEventError, RuntimeError):
  message = "Unable to find repodata folder for repo '%(repoid)s' at '%(url)s'"

class InvalidRepomdFileError(DeployEventError, RuntimeError):
  message = "%(message)s"

class InconsistentRepodataError(DeployEventError, RuntimeError):
  message = ( "Unable to obtain consistent value for one or more checksums "
              " in repo '%(repoid)s' after %(ntries)d tries" )

class SystemidIOError(DeployIOError):
  message = ( "Unable to read systemid file '%(file)s' for repo "
              "'%(repoid)s': [errno %(errno)d] %(message)s" )

class SystemidUndefinedError(DeployEventError, InvalidConfigError):
  message = "No <systemid> element defined for repo '%(repoid)s'"

class SystemidInvalidError(DeployEventError):
  message = ( "Systemid file '%(file)s' for repo '%(repo)s' is invalid: "
              "%(message)s" )

class PkgsfileIOError(DeployIOError):
  message = ( "Unable to compute package version for %(names)s with pkgsfile "
              "'%(file)s': [errno %(errno)d] %(message)s" )

class DeployRepoFileParseError(DeployEventError):
  message = "Error parsing repo file: %(message)s"

class RepomdCsumMismatchError(DeployEventError):
  message = ( "Checksum of file '%(file)s' doesn't match repomd.xml for "
              "repo '%(repoid)s':\n"
              "  Got:      %(got)s\n"
              "  Expected: %(expected)s" )

class MirrorlistFormatInvalidError(DeployEventError):
  message = ( "Mirrorlist format invalid for repo '%(repo)s' on line "
              "%(lineno)d: '%(line)s': %(reason)s" )
