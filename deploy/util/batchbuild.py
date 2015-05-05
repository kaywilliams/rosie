#!/usr/bin/python
#
# Copyright (c) 2015
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
"""
batchbuild.py

base class for building definitions in a batch process.
"""

# list of definitions in ("definition", "command-line-options") format
buildlist = [
("test.definition", "--debug --log-level=0"),
("test2.definition", "--macro name:value")
]

import os

from deploy.main import Build

class BatchBuild:
  def __init__(self, buildlist=[]):
    for file,opts in buildlist:
      # setup
      self.setup(opts, file)

      # build definition
      self.build()

      # get id
      self.id = self.builder.build_id

      # get datadir
      self.datadir = self.builder.data_dir

      # commit datafiles
      self.commit()

  def setup(self, opts, file):
    print # blank line 
    # customize file before it is parsed, if desired
    self.builder = Build(opts, file)
    # or after using lxml and self.builder.definition

  def build(self):
    self.builder.main()

  def commit(self):
    os.chdir(self.datadir)
    # addremove files
    # commit added/removed/modified files
    # use self.id in commit message


if __name__ == '__main__': BatchBuild(buildlist)
