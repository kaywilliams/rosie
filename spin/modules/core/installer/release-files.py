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
from spin.constants import SRPM_REGEX
from spin.event     import Event

from spin.modules.shared import ExtractMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ReleaseFilesEvent'],
  description = 'extracts files from a release RPM to the os folder',
  group       = 'installer',
)

DEFAULT_SET = ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README*',
               '*-RPM-GPG', 'RPM-GPG-KEY*', 'RELEASE-NOTES*']

class ReleaseFilesEvent(Event, ExtractMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'release-files',
      parentid = 'installer',
      requires = ['rpms-directory'],
      conditionally_comes_after = ['gpgsign'],
    )

    self.DATA = {
      'variables': ['name'],
      'config':    ['.'],
      'input' :    [],
      'output':    [],
    }
    self.rpms = None

  def setup(self):
    self.rpms = self._find_rpms()
    if self.rpms is not None:
      self.DATA['input'].extend(self.rpms)
    self.diff.setup(self.DATA)
    self.io.add_xpath('path', self.SOFTWARE_STORE, id='release-files-input')

  def run(self):
    self.cvars.setdefault('release-files', [])
    if ( self.rpms and
         self.config.getbool('@extract-rpm-files', 'True') ):
      self._extract()
    self.io.sync_input(link=True, cache=False, what='release-files-input')

  def apply(self):
    existing = []
    for item in DEFAULT_SET:
      existing.extend(self.SOFTWARE_STORE.listdir(glob=item))
    if existing:
      self.cvars.setdefault('release-files', []).extend(existing)
    self.io.clean_eventcache()

  def _generate(self, working_dir):
    rtn = []
    for item in DEFAULT_SET:
      for file in working_dir.findpaths(glob=item):
        self.link(file, self.SOFTWARE_STORE)
        rtn.append(self.SOFTWARE_STORE / file.basename)
    self.cvars['release-files'].extend(rtn)
    return rtn

  def _find_rpms(self):
    rpmnames = self.config.xpath('package/text()', [ '%s-release' % self.name ])
    rpmset = set()
    for rpmname in rpmnames:
      for rpm in self.cvars['rpms-directory'].findpaths(
          glob='%s-*-*' % rpmname, nregex=SRPM_REGEX):
        rpmset.add(rpm)

    if not rpmset:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        for rpm in self.cvars['rpms-directory'].findpaths(
            glob=glob, nglob='*%s-*' % self.name, nregex=SRPM_REGEX):
          rpmset.add(rpm)
        if not rpmset:
          return None
    return rpmset

  def verify_cvars(self):
    "verify all cvars exist"
    self.verifier.failUnlessSet('release-files')
