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
      provides = ['kickstart-file', 'ks-path', 'initrd-image-content'],
      requires = ['user-required-packages', 'user-required-groups',
                  'user-excluded-packages', 'web-path'],
    )

    self.DATA = {
      'config':    ['.'],
      'input':     [],
      'output':    [],
      'variables': [],
    }

    self.ksfile = None # set in setup


  def setup(self):
    self.diff.setup(self.DATA)
    self.io.add_xpath('.', self.SOFTWARE_STORE, id='kickstart-file')
    self.ksfile = self.io.list_output(what='kickstart-file')[0]

  def _read_kickstart(self, path):
    ks = ksparser.KickstartParser(
           ksversion.makeVersion(self.locals.L_KICKSTART)
         )

    ks.readKickstart(path)
    return ks

  def run(self):
    self.io.sync_input(cache=True)

    ks = self._read_kickstart(self.ksfile)

    # modify repos
    self._update_repos(ks,
                       ['--name', 'appliance',
                        '--baseurl', self.cvars['web-path']])
    self.DATA['variables'].append('cvars[\'repodata-directory\']')

    # modify %packages
    self._update_packages(ks, groups   = self.cvars['user-required-groups'],
                              packages = self.cvars['user-required-packages'],
                              excludes = self.cvars['user-excluded-packages'])
    self.DATA['variables'].append('cvars[\'user-required-groups\']')
    self.DATA['variables'].append('cvars[\'user-required-packages\']')
    self.DATA['variables'].append('cvars[\'user-excluded-packages\']')

    # write out updated file
    self.ksfile.write_text(str(ks.handler))

  def _update_repos(self, ks, args):
    ks.handler.repo.repoList = []
    ks.handler.repo.parse(args)

  def _update_packages(self, ks, groups=None, packages=None, excludes=None):
    ks.handler.packages.excludedList = []
    ks.handler.packages.groupList    = []
    ks.handler.packages.packageList  = []

    lines = []

    if groups:   lines.extend([ '@'+x for x in groups ])
    if packages: lines.extend(packages)
    if excludes: lines.extend([ '-'+x for x in excludes ])

    ks.handler.packages.add(lines)

  def apply(self):
    self.cvars['kickstart-file'] = self.ksfile
    self.cvars['ks-path']        = '/' / self.ksfile.basename
    self.cvars['kickstart']      = self._read_kickstart(self.ksfile)

  def verify_cvars(self):
    "cvars are set"
    self.verifier.failUnlessSet('kickstart-file')
    self.verifier.failUnlessSet('ks-path')
    self.verifier.failUnlessSet('kickstart')


#import sha

#  def prep_scripts(self):
#    scripts = []
#    for s in self.ks.handler.scripts:
#      scripts.append(dict(scriptsha = sha.new(s.script).hexdigest(),
#                          interp    = s.interp,
#                          inChroot  = s.inChroot,
#                          type      = s.type))
#    return scripts
