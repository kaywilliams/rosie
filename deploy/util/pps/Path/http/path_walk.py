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
import re
import stat

from deploy.util.pps.Path.remote import RemotePath_Walk

from deploy.util.pps.constants import *
from deploy.util.pps.PathSet   import PathSet

from deploy.util.pps.Path.error import PathError

# url REs to ignore
BLACKLIST = [
  re.compile('^\?'),      # query
  re.compile('^\.\.'),    # upward relative path
  re.compile('^/'),       # absolute path
  re.compile('^;'),       # parameter
  re.compile('^#'),       # fragment
  re.compile('^mailto:'), # mailto
  re.compile('://'),      # full URLs
]

HYPERLINK = re.compile('<a .*href=\"(?P<url>[^\"]*)\".*>')

class HttpPath_Walk(RemotePath_Walk):

  def listdir(self, glob=None, nglob=None, all=False, sort='name'):
    fo = self._open()

    try:
      if not self.isdir(): raise PathError(20, self)

      index = fo.read()
    finally:
      fo.close()

    content = []
    for link in HYPERLINK.findall(index):
      link = HYPERLINK.sub('\g<url>', link)

      try:
        for item in BLACKLIST:
          if item.findall(link): raise StopIteration
      except StopIteration:
        continue

      content.append(link)

    pathset = PathSet()
    for item in content:
      if item.endswith(self._pypath.sep):
        mode = stat.S_IFDIR
      else:
        mode = stat.S_IFREG
      path = self/item
      path.stat(populate=False).update(st_mode=mode)
      #path = Path(path.rstrip('/')) # remove directory indicator
      pathset.append(path)

    if glob:  pathset.fnmatch(glob)
    if nglob: pathset.fnmatch(nglob, invert=True)
    if sort:  pathset.sort(type=sort)

    return pathset
