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

from rendition import pps

from spin.event import Event

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
      provides = ['kickstart', 'kickstart-file', 'ks-path',
                  'initrd-image-content'],
      requires = ['user-required-packages', 'comps-group-info',
                  'user-excluded-packages', 'repodata-directory'],
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'output':    [],
      'variables': ['cvars[\'repodata-directory\']',
                    'cvars[\'user-required-groups\']',
                    'cvars[\'user-required-packages\']',
                    'cvars[\'user-excluded-packages\']'],
    }

    self.ksfile = None

  def setup(self):
    self.ksfile = self.SOFTWARE_STORE / 'ks.cfg'
    self.diff.setup(self.DATA)
    self.DATA['output'].append(self.ksfile)

  def run(self):
    ks = self._read_kickstart_from_string(self.config.text or '')

    # modify repos
    ## problem - repodata-directory will only work for local vm builds
    ## problem - web-path will only work if publish is executed before vms
    self._update_repos(ks,
          ['--name', 'appliance',
           '--baseurl', 'file://'+self.cvars['repodata-directory'].dirname])

    # modify %packages
    self._update_packages(ks, groups   = self.cvars['comps-group-info'],
                              packages = self.cvars['user-required-packages'],
                              excludes = self.cvars['user-excluded-packages'])

    # modify partitions (iff missing)
    if len(ks.handler.partition.partitions) == 0:
      self._update_partitions(ks,
            ['/', '--size', '550', '--fstype', 'ext3', '--ondisk', 'sda'])

    # update partition so it doesn't write out deprecated bytes-per-inode
    # in F9 and greater; this is kind of stupid
    if self.locals.L_KICKSTART >= ksversion.F9:
      for part in ks.handler.partition.partitions:
        part.bytesPerInode = 0

    # write out updated file
    self.ksfile.write_text(str(ks.handler))

  def apply(self):
    self.cvars['kickstart-file'] = self.ksfile
    self.cvars['ks-path']        = '/' / self.ksfile.basename
    self.cvars['kickstart']      = self._read_kickstart(self.ksfile)

  def verify_cvars(self):
    "cvars are set"
    self.verifier.failUnlessSet('kickstart-file')
    self.verifier.failUnlessSet('ks-path')
    self.verifier.failUnlessSet('kickstart')

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

  def _update_packages(self, ks, groups=None, packages=None, excludes=None):
    ks.handler.packages.excludedList = []
    ks.handler.packages.groupList    = []
    ks.handler.packages.packageList  = []

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
