#
# Copyright (c) 2012
# System Studio Project. All rights reserved.
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

from systemstudio.util.pps.Path.http import HttpPath_IO

from error import error_transform

class RhnPath_IO(HttpPath_IO):

  def open(self, *args, **kwargs):
    # convert self to the 'real' path and return that
    return self.touri().open(*args, **kwargs)

  _protect = ['utime', 'chmod', 'chown', 'rename', 'mkdir', 'rmdir', 'mknod',
              'touch', 'remove', 'unlink', 'link', 'symlink', 'readlink',
              'open']


for fn in RhnPath_IO._protect:
  setattr(RhnPath_IO, fn, error_transform(getattr(RhnPath_IO, fn)))
