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
import pykickstart.parser  as ksparser
import pykickstart.version as ksversion
from pykickstart.constants import KS_MISSING_PROMPT, KS_MISSING_IGNORE

from rendition import pps

from systembuilder.event  import Event
from systembuilder.errors import SystemBuilderError, assert_file_readable

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['KickstartEvent'],
  description = 'include a kickstart for bare-metal and '
                'virtual machine installations',
)

class KickstartEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'kickstart',
      parentid = 'os',
      version = 1,
      provides = ['local-baseurl-kickstart',
                  'local-baseurl-kickstart-file',
                  'local-baseurl-ks-path',
                  'remote-baseurl-kickstart',
                  'remote-baseurl-kickstart-file',
                  'remote-baseurl-ks-path',
                  'initrd-image-content'],
      requires = ['user-required-packages', 'comps-group-info',
                  'user-excluded-packages', 'repodata-directory'],
      conditionally_requires = ['web-path']
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'output':    [],
      'variables': ['cvars[\'repodata-directory\']',
                    'cvars[\'comps-group-info\']',
                    'cvars[\'user-required-groups\']',
                    'cvars[\'user-required-packages\']',
                    'cvars[\'user-excluded-packages\']'],
    }

    self.local_ksfile  = None
    self.remote_ksfile = None

  def setup(self):
    self.diff.setup(self.DATA)

    self.remote_ksfile = self.SOFTWARE_STORE / 'ks.cfg'
    self.local_ksfile  = self.mddir / 'ks.cfg'
    self.DATA['output'].append(self.local_ksfile)
    if self.cvars['web-path']:
      self.DATA['output'].append(self.remote_ksfile)

  def run(self):
    ks = self._read_kickstart_from_string(self.config.text or '')

    self._validate_kickstart(ks)

    # modify %packages
    self._update_packages(ks,
      groups        = self.cvars['comps-group-info'],
      packages      = self.cvars['user-required-packages'],
      excludes      = self.cvars['user-excluded-packages'],
      default       = self.cvars['packages-default'],
      excludeDocs   = self.cvars['packages-excludedocs'],
      handleMissing = self.cvars['packages-ignoremissing'])

    # modify partitions (iff missing)
    if len(ks.handler.partition.partitions) == 0:
      self._update_partitions(ks,
            ['/', '--size', '550', '--fstype', 'ext3', '--ondisk', 'sda'])

    # update partition so it doesn't write out deprecated bytes-per-inode
    # in F9 and greater; this is kind of stupid
    if self.locals.L_KICKSTART >= ksversion.F9:
      for part in ks.handler.partition.partitions:
        part.bytesPerInode = 0

    # modify repos to have local baseurl
    self._update_repos(ks,
          ['--name', 'distribution',
           '--baseurl', 'file://'+self.cvars['repodata-directory'].dirname])

    # write out ks file with the local baseurl
    self.local_ksfile.write_text(str(ks.handler))

    # if we're publishing to a web-accesible location, also write out a
    # kickstart with repos pointing to the web location
    if self.cvars['web-path']:
      self._update_repos(ks,
            ['--name', 'distribution',
             '--baseurl', self.cvars['web-path'] / 'os' ])

      # write out the ks file with the remote baseurl
      self.remote_ksfile.dirname.mkdirs()
      self.remote_ksfile.write_text(str(ks.handler))

  def apply(self):
    self.io.clean_eventcache()

    assert_file_readable(self.local_ksfile)
    self.cvars['local-baseurl-kickstart-file'] = self.local_ksfile
    self.cvars['local-baseurl-ks-path']        = '/' / self.local_ksfile.basename
    self.cvars['local-baseurl-kickstart']      = self._read_kickstart(self.local_ksfile)

    if self.cvars['web-path']:
      assert_file_readable(self.remote_ksfile)
      self.cvars['remote-baseurl-kickstart-file'] = self.remote_ksfile
      self.cvars['remote-baseurl-ks-path']        = '/' / self.remote_ksfile.basename
      self.cvars['remote-baseurl-kickstart']      = self._read_kickstart(self.remote_ksfile)

  def verify_cvars(self):
    "cvars are set"
    self.verifier.failUnlessSet('local-baseurl-kickstart-file')
    self.verifier.failUnlessSet('local-baseurl-ks-path')
    self.verifier.failUnlessSet('local-baseurl-kickstart')

    if self.cvars['web-path']:
      self.verifier.failUnlessSet('remote-baseurl-kickstart-file')
      self.verifier.failUnlessSet('remote-baseurl-ks-path')
      self.verifier.failUnlessSet('remote-baseurl-kickstart')

  def _validate_kickstart(self, ks):
    if ks.handler.repo.repoList:
      raise RepoSpecifiedError()
    if ( ks.handler.packages.excludedList or
         ks.handler.packages.groupList or
         ks.handler.packages.packageList ):
      raise PackagesSpecifiedError()

  def _read_kickstart_from_string(self, string):
    ks = ksparser.KickstartParser(
           ksversion.makeVersion(self.locals.L_KICKSTART)
         )

    ks.readKickstartFromString(string)
    return ks

  def _read_kickstart(self, path):
    ks = ksparser.KickstartParser(
           ksversion.makeVersion(self.locals.L_KICKSTART)
         )

    ks.readKickstart(path)
    return ks

  def _update_repos(self, ks, args):
    ks.handler.repo.repoList = []
    ks.handler.repo.parse(args)

  def _update_partitions(self, ks, args):
    ks.handler.partition.partitions = []
    ks.handler.partition.parse(args)

  def _update_packages(self, ks, groups=None, packages=None, excludes=None,
                                 default=None, excludeDocs=None,
                                 handleMissing=None):
    ks.handler.packages.excludedList  = []
    ks.handler.packages.groupList     = []
    ks.handler.packages.packageList   = []

    if default is not None:
      ks.handler.packages.default       = default
    if excludeDocs is not None:
      ks.handler.packages.excludeDocs   = excludeDocs
    if handleMissing is not None:
      ks.handler.packages.handleMissing = \
        handleMissing and KS_MISSING_PROMPT or KS_MISSING_IGNORE

    lines = []

    if groups:
      for (grpid, default, optional) in groups:
        line = '@%s' % grpid
        if not default:
          line = '%s --nodefaults' % line
        if optional:
          line = '%s --optional' % line
        lines.append(line)
    if packages: lines.extend(packages)
    if excludes: lines.extend([ '-'+x for x in excludes ])

    ks.handler.packages.add(lines)


class RepoSpecifiedError(SystemBuilderError):
  message = "Cannot specify repo command in the kickstart contents."
class PackagesSpecifiedError(SystemBuilderError):
  message = "Cannot specify packages section in kickstart contents."
