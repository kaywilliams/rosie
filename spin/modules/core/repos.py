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

from rendition.repo    import ReposFromXml, ReposFromFile, RepoContainer
from rendition.versort import Version

from spin.event    import Event
from spin.logging  import L1, L2
from spin.validate import InvalidConfigError

from spin.modules.shared import RepoEventMixin, SpinRepo

API_VERSION = 5.0
EVENTS = {'setup': ['ReposEvent']}

class ReposEvent(RepoEventMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'repos',
      version = 2,
      provides = ['anaconda-version',
                  'logos-versions',
                  'release-versions',
                  'repos',
                  'input-repos', # ugly solution to cycle in release-rpm, custom-repo
                  'comps-excluded-packages',
                  'pkglist-excluded-packages'],
      conditionally_requires = ['base-distro',
                                'anaconda-version-supplied'],
    )
    RepoEventMixin.__init__(self)

    self.DATA = {
      'variables': [], #more later from self.setup_repos()
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }


  def setup(self):
    self.diff.setup(self.DATA)

    # additional repos to include with defaults, if any
    addrepos = RepoContainer()
    if self.config.pathexists('.'):
      addrepos.add_repos(ReposFromXml(self.config.get('.'), cls=SpinRepo))
    for filexml in self.config.xpath('repofile', []):
      addrepos.add_repos(ReposFromFile(self._config.file.dirname / filexml.text,
                                       cls=SpinRepo))

    self.setup_repos('packages', updates=addrepos)
    self.read_repodata()
    for repo in self.repos.values():
      try:
        (repo.url//'repodata').exists()
      except OSError, e:
        raise RuntimeError(str(e))

  def run(self):
    self.sync_repodata()

    # process available package lists
    self.log(1, L1("reading available packages"))
    self.read_packages()

  def apply(self):
    self.io.clean_eventcache()

    anaconda_version = None

    for repo in self.repos.values():
      # read repocontent
      try:
        repo.repocontent.read(repo.pkgsfile)
      except Exception, e:
        raise RuntimeError(str(e))

      # get logos and release versions, if any in repo
      for pkgid,allpkgs in RPMDATA.items(): # see below
        n,v = repo.get_rpm_version(allpkgs)
        if n is not None and v is not None:
          self.cvars.setdefault(pkgid, []).append((n,'==',v))

      # get anaconda version
      n,v = repo.get_rpm_version(['anaconda'])
      if n and v:
        if not anaconda_version or v > anaconda_version:
          anaconda_version = v

    if not anaconda_version and not self.cvars['anaconda-version-supplied']:
      raise RuntimeError("Unable to find the 'anaconda' package in any "
                         "specified repository, and 'anaconda-version' "
                         "not given in <installer>")
    else:
      self.cvars['anaconda-version'] = \
        self.cvars['anaconda-version-supplied'] or anaconda_version

    self.cvars['repos']  = self.repos

    # globally excluded packages
    global_excludes = self.config.xpath('exclude-package/text()', [])
    self.cvars.setdefault('comps-excluded-packages', set()).update(global_excludes)
    self.cvars.setdefault('pkglist-excluded-packages', set()).update(global_excludes)

  def verify_pkgsfiles_exist(self):
    "verify all pkgsfiles exist"
    for repo in self.repos.values():
      self.verifier.failUnlessExists(repo.pkgsfile)

  def verify_repodata(self):
    "repodata exists"
    for repo in self.repos.values():
      self.verifier.failUnlessExists(repo.localurl / repo.repomd)
      self.verifier.failUnlessExists(repo.localurl / repo.datafiles['primary'])

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnless(self.cvars['repos'])
    self.verifier.failUnless(self.cvars['anaconda-version'])


#------ ERRORS ------#
class RepoNotFoundError(StandardError): pass

#------ LOCALS ------#
# maps an rpm type to the names of rpms for the 'category'
RPMDATA = { 'logos-versions':   [ 'fedora-logos',
                                  'centos-logos',
                                  'redhat-logos' ],
            'release-versions': [ 'fedora-release',
                                  'centos-release',
                                  'redhat-release',
                                  'fedora-release-notes',
                                  'centos-release-notes',
                                  'redhat-release-notes' ] }
