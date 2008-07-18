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

import re
import sha
import time

from rendition import pps
from rendition import rxml

from rendition.difftest.filesdiff import DiffTuple

from rendition.pps.constants import TYPE_DIR

from spin.logging   import L1, L2
from spin.constants import BOOLEANS_TRUE, BOOLEANS_FALSE

from rendition.repo          import ReposFromXml, ReposFromFile, getDefaultRepos
from rendition.repo.repo     import YumRepo, RepoContainer, NSMAP
from rendition.repo.defaults import TYPE_ALL

__all__ = ['RepoEventMixin', 'SpinRepo', 'SpinRepoGroup']

# list of folders that don't contain repodata folders for sure
NOT_REPO_GLOB = ['images', 'isolinux', 'repodata', 'repoview',
                 'stylesheet-images']

class SpinRepo(YumRepo):
  keyfilter = ['id', 'systemid']

  def __init__(self, **kwargs):
    YumRepo.__init__(self, **kwargs)
    self.localurl = None
    self._systemid = None # system id, for redhat mirrors

  def _boolparse(self, s):
    if s in BOOLEANS_FALSE:
      return False
    elif s in BOOLEANS_TRUE:
      return True
    elif s is None:
      return None
    else:
      raise ValueError('invalid boolean value')

  @property
  def pkgsfile(self):
    return self.localurl/'packages'

  def _pkg_filter(self, pkg):
    """Returns True if this repo can have the given pkg based on exclude
    and includepkgs.  Doesn't actually check to see if pkg is in the repo."""
    if pkg in self.exclude: return False
    if self.includepkgs: return pkg in self.includepkgs
    return True

  def get_rpm_version(self, names):
    # filter list of names if necessary
    names = [ n for n in names if self._pkg_filter(n) ]
    if not names: return (None, None)

    scan = re.compile('(?:.*/)?(' + '|'.join(names) + ')-(.*)(\..*\..*$)')
    if not self.pkgsfile.exists():
      raise RuntimeError("Unable to compute package version for '%s': "
                         "pkgsfile '%s' does not exist."
                         % (names, self.pkgsfile))
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
        p.systemid = pps.path(self.get('systemid'))
        if p.systemid:
          p.systemid = p.systemid.realpath()
          if not p.systemid.exists():
            raise RuntimeError("unable to find systemid at '%s'" % p.systemid)
      else:
        p = YumRepo._xform_uri(self, p)
    except (AttributeError):
      p = YumRepo._xform_uri(self, p)
    return p

class RhnSpinRepo(SpinRepo):
  # redhat's RHN repos are very annoying in that they have inconsitent
  # metadata at times.  This class aims to account for this instability

  EMPTY_FILE_CSUM = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
  MAX_TRIES = 5 # number of times to try redownloading repomd

  def read_repomd(self):
    i = 0; consistent = False
    while i < self.MAX_TRIES:
      SpinRepo.read_repomd(self)
      if self.EMPTY_FILE_CSUM not in \
        self.repomd.xpath('//repo:data/repo:checksum/text()',
                          namespaces=NSMAP):
        consistent = True; break
      i += 1
    if not consistent:
      raise RuntimeError("Unable to obtain consistent value for one "
                         "or more checksums in repo '%s' after %d tries"
                         % (self.id, self.MAX_TRIES))


class SpinRepoGroup(SpinRepo):
  def __init__(self, **kwargs):
    SpinRepo.__init__(self, **kwargs)

    self._repos = None
    self.has_installer_files = False

  def _populate_repos(self):
    "Find all the repos we contain and classify ourself"
    self._repos = RepoContainer()

    # need special handling for rhn paths
    cls = SpinRepo
    try:
      if isinstance(self.url.realm, pps.Path.rhn.RhnPath):
        cls = RhnSpinRepo
    except AttributeError:
      if self.url.realm.startswith('rhn://') or \
         self.url.realm.startswith('rhns://'):
        raise ValueError("RHN path support not enabled - please install "
                         "the 'rhnlib' and 'rhn-client-tools' packages.")
      pass

    # get directory listing so we can figure out information about this repo
    # find all subrepos
    repos = []
    if (self.url/'repodata/repomd.xml').exists():
      updates = {}
      for k,v in self.items():
        if k not in ['id']:
          updates[k] = v
      R = cls(id=self.id, **updates)
      R._relpath = pps.path('.')
      self._repos.add_repo(R)
    else:
      for d in self.url.findpaths(type=TYPE_DIR, mindepth=1, maxdepth=1,
                                  nglob=NOT_REPO_GLOB):
        if (d/'repodata/repomd.xml').exists():
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
          self._repos.add_repo(R)

    if len(self._repos) == 0:
      raise RuntimeError("Unable to find repodata folder for repo '%s' at '%s'"
                          % (self.id, self.url.realm))

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
    return l

  def read_repomd(self):
    for R in self.subrepos.values():
      R.read_repomd()
      for k,v in R.datafiles.items():
        self.datafiles.setdefault(k, []).append(R._relpath/v)

  @property
  def subrepos(self):
    if not self._repos:
      self._populate_repos()
    return self._repos

class RepoEventMixin:
  def __init__(self):
    self.repos = RepoContainer()

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
      self.repos.add_repo(R)

    for repo in self.repos.values():
      # remove disabled repos
      if not repo.enabled:
        self.log(5, L1("Removing disabled repo '%s'" % repo.id))
        del self.repos[repo.id]
        continue

      # set $yumvars
      repo.vars['$releasever'] = self.config.get('releasever/text()', self.version)
      repo.vars['$basearch']   = self.config.get('basearch/text()',   self.basearch)

    # make sure we got at least one repo out of that mess
    if not len(self.repos) > 0:
      raise RuntimeError("No enabled repos in <%s>" % self.id)

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
      repo.read_repomd()

      # add metadata to io sync
      for r in repo.subrepos.values():
        # first handle all repomd files except repomd.xml
        for k,v in r.datafiles.items():
          if k == 'metadata': continue # skip repomd.xml; handle later
          # prepopulate the checksum so we don't have to compute it later
          csum = r.repomd.get('repo:data[@type="%s"]/repo:checksum/text()' % k,
                              namespaces=NSMAP)
          ( pps.lib.CACHE.setdefault((r.url/v).normpath(), {})
                         .setdefault('shasum', csum) )

        # now handle repomd.xml
        src_csums = r.repomd.xpath('//repo:data/repo:checksum/text()',
                                   namespaces=NSMAP)

        dst_repomd = self.mddir/repo.id/r._relpath/r.repomdfile
        # get the cached file location and check there as well - the output
        # file might not exist due to errors, etc
        csh_repomd = (self.cache_handler.cache_dir /
                      self.cache_handler._gen_hash((r.url/r.repomdfile).normpath()))

        if dst_repomd.exists():
          repomdfile = dst_repomd
        elif csh_repomd.exists():
          repomdfile = csh_repomd
        else:
          repomdfile = None

        # compute destination checksums from repomd.xml on disk, if exists
        dst_csums = []
        if repomdfile is not None:
          repomdxml = rxml.tree.read(repomdfile)
          dst_csums = repomdxml.xpath('//repo:data/repo:checksum/text()',
                                      namespaces=NSMAP)

        # if destination file exists and is the same as the source, set its
        # mtime to be the same so that it isn't redownloaded
        if src_csums == dst_csums and repomdfile is not None:
          mtime = repomdfile.stat().st_mtime
        else:
          mtime = time.time()

        # finally, set up the sync process
        for k,v in r.datafiles.items():
          self.io.add_fpath(r.url/v, self.mddir/repo.id/r._relpath/v.dirname,
                            id='%s-repodata' % repo.id)
          (r.url/v).stat().update(st_mtime=mtime)

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
      self.io.sync_input(what='%s-repodata' % repo.id, cache=True,
                         text=("downloading repodata - '%s'" % repo.id))

  def read_packages(self):
    """
    After synchronizing repository metadata, this method reads in the list
    of packages, along with size and mtime information about each one, from
    the primary.xml.gz.  This is only done for primary.xml.gz files that
    actually change, or for new repositories.  After reading this data in,
    it is written out to the repository's pkgsfile.

    This method should typically be called in Event.run(), after calling
    .sync_repodata(), above.  Each repo's .localurl attribute must also be
    set (normally handled via .setup_repos(), also above).
    """
    # compute the set of old and new repos
    difftup = self.diff.variables.difference('repoids')
    newids = set()
    if difftup:
      prev,curr = difftup
      if not isinstance(prev, list): prev = [] # ugly hack; NewEntry not iterable
      newids = set(curr).difference(prev)

    for repo in self.repos.values():
      doupdate = repo.id in newids or not repo.pkgsfile.exists()
      if not doupdate:
        for pxml in repo.datafiles['primary']:
          if self.diff.input.difference((repo.url//pxml).normpath()):
            doupdate = True
            break

      if doupdate:
        self.log(2, L2(repo.id))
        repo.repocontent.clear()
        for pxml in repo.datafiles['primary']:
          repo.repocontent.update(pxml, clear=False)
        repo.repocontent.write(repo.pkgsfile)

      self.DATA['output'].append(repo.pkgsfile) # add pkgsfile to output

class ReposDiffTuple(DiffTuple):
  attrs = DiffTuple.attrs + [('csum', str)]

  def __init__(self, path=None):
    DiffTuple.__init__(self, path)

    self.csum = None

    # hack so we don't end up downloading repomd.xml 3 times...
    if self.mtime == -1 and self.path.basename != 'repomd.xml':
      # if mtime is -1, the path must exist, so we don't need try/except
      self.csum = self.path.shasum()
