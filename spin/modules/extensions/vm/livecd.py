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
livecd.py

Creates a livecd image (.iso)
"""

import imgcreate

from spin.event   import Event

MODULE_INFO = dict(
  api    = 5.0,
  events = ['LivecdEvent'],
)

class LivecdEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'livecd',
      parentid = 'vm',
      provides = ['livecd-image'],
      requires = ['os-dir', 'repos', 'repodata-directory']
    )

    self.vmdir = self.mddir / 'vms'

    self.DATA =  {
      'config': ['.'],
      'input':  [],
      'output': [self.vmdir],
      'variables': ['cvars[\'repos\']', 'cvars[\'repodata-directory\']'],
    }

    self.creator = None

  def setup(self):
    self.diff.setup(self.DATA)

    # read supplied kickstart
    ks = imgcreate.read_kickstart(self.config.getpath('.'))
    self.DATA['input'].append(self.config.getpath('.'))

    # replace repos in kickstart if present
    ks.handler.repo.repoList = []
    ks.handler.repo.parse(['--name', 'appliance',
                           '--baseurl', 'file://%s' % self.cvars['repodata-directory'].dirname])

    # create image creator
    self.vmdir.mkdirs()
    self.creator = imgcreate.LiveImageCreator(ks, '%s-livecd' % self.applianceid)

  def run(self):
    ## todos
    ## shell command outputs - too verbose for standard run
    ## hook up logging to spin, either by modifying spin or modyfing imgcreate
    ## performance optimization - don't delete installroot and use yum update
    ## squashfs creation is slooooooowwwwww....

    try:
      self.creator.mount(cachedir=self.mddir/'build')
      self.creator.install()
      self.creator.configure()
      self.creator.unmount()
      self.creator.package(self.vmdir)
    finally:
      self.creator.cleanup()

  def apply(self):
    self.io.clean_eventcache()

    self.cvars.setdefault('publish-content', set()).add(self.vmdir)

  def error(self, e):
    self.creator and self.creator.cleanup()
    Event.error(self, e)
