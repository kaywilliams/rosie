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

from rendition.versort import Version

from spin.event    import Event
from spin.logging  import L1, L2
from spin.validate import InvalidConfigError

from spin.modules.shared import RepoEventMixin

API_VERSION = 5.0
EVENTS = {'setup': ['ReposEvent']}

class ReposEvent(Event, RepoEventMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'repos',
      version = 1,
      provides = ['anaconda-version',
                  'logos-versions',
                  'release-versions',
                  'repos',         # provided by repos and localrepo events
                  'input-repos',   # provided by repos event only, used by release-rpm
                  'base-repoid',
                  'comps-excluded-packages',
                  'pkglist-excluded-packages',
                  ],
    )
    RepoEventMixin.__init__(self)

    self.DATA = {
      'variables': [], # filled later by read_config
      'config':    ['.'],
      'input':     [],
      'output':    [],
    }

  def validate(self):
    if self.config.get('base-repo/text()', None) is None:
      raise InvalidConfigError(self.config,
         "Config file must define a 'base-repo' element with the id "
         "of the base repo to use in spin processing")
    if self.config.get('repo', None) is None and \
       self.config.get('repofile', None) is None:
      raise InvalidConfigError(self.config,
         "Config file must specify at least one 'repo' element or "
         "at least one 'repofile' element as a child to the 'repos' "
         "element.")

  def setup(self):
    self.diff.setup(self.DATA)
    self.cvars['base-repoid'] = self.config.get('base-repo/text()')
    self.read_config(repos='repo', files='repofile')

  def run(self):
    self.sync_repodata()

    # process available package lists
    self.log(1, L1("reading available packages"))
    self.read_new_packages()

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    for repo in self.repocontainer.values():
      try: # hack
        repo._read_repo_content(repofile=repo.pkgsfile)
      except:
        continue

      # get anaconda_version, if base repo
      if repo.id == self.cvars['base-repoid']:
        anaconda_version = get_package_version(['anaconda'], repo.pkgsfile)
        if anaconda_version is not None:
          name, version = anaconda_version
          self.cvars['anaconda-version'] = Version(version)
        else:
          raise ValueError("unable to compute anaconda version from distro metadata")

      # get logos and release versions, if any in repo
      pkgs = {'logos-versions': ['fedora-logos', 'centos-logos', 'redhat-logos'],
              'release-versions': ['fedora-release', 'centos-release', 'redhat-release',
                                   'fedora-release-notes', 'centos-release-notes',
                                   'redhat-release-notes']}

      for pkg in pkgs:
        pkg_version = get_package_version(pkgs[pkg], repo.pkgsfile)
        if pkg_version is not None:
          name, version = pkg_version
          self.cvars.setdefault(pkg, []).append((name, '==', version))

    self.cvars['repos'] = self.repocontainer

    if self.cvars['base-repoid'] not in self.repocontainer.keys():
      raise ValueError("Base repo id '%s' not found in any repo definition or "
                       "repo file given in config" % self.cvars['base-repoid'])

    # globally excluded packages
    global_excludes = self.config.xpath('exclude-package/text()', [])
    self.cvars.setdefault('comps-excluded-packages', set()).update(global_excludes)
    self.cvars.setdefault('pkglist-excluded-packages', set()).update(global_excludes)

  def verify_pkgsfiles_exist(self):
    "verify all pkgsfiles exist"
    for repo in self.repocontainer.values():
      self.verifier.failUnlessExists(repo.pkgsfile)

  def verify_repodata(self):
    "repodata exists"
    for repo in self.repocontainer.values():
      self.verifier.failUnlessExists(repo.localurl / repo.mdfile)
      self.verifier.failUnlessExists(repo.localurl /
                                     'repodata' /
                                     repo.datafiles['primary'])

  def verify_cvars(self):
    "verify cvars are set"
    self.verifier.failUnless(self.cvars['anaconda-version'])
    self.verifier.failUnless(self.cvars['repos'])
    self.verifier.failUnless(self.cvars['base-repoid'])


#------ HELPER FUNCTIONS ------#
def get_package_version(names, file):
  scan = re.compile('(?:.*/)?(' + "|".join(names) + ')-(.*)(\..*\..*$)')
  fl = file.read_lines()
  for rpm in fl:
    match = scan.match(rpm)
    if match:
      try:
        return match.groups()[0], match.groups()[1]
      except (AttributeError, IndexError), e:
        pass
  return None


#------ ERRORS ------#
class RepoNotFoundError(StandardError): pass

