#
# Copyright (c) 2010
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
"link.py - a CopyHandler object for linking files instead of copying them"

__author__  = 'Daniel Musgrave <dmusgrave@renditionsoftware.com>'
__version__ = '0.8.1'
__date__    = 'August 22nd, 2007'

from systembuilder.util.pps.Path.error import PathError

from systembuilder.util.sync.__init__  import CopyHandler, SyncOperation, SyncError

#------ SYNC HANDLER ------#
class LinkHandler(CopyHandler):
  "Creates a link from fsrc to fdst"
  def __init__(self, allow_xdev=False, xdev_copy_handler=None):
    """
    allow_xdev        : whether or not to allow cross-device 'links' - hard
                        links can't be created across devices, but setting
                        this flag will copy the file if such a situation
                        arises
    xdev_copy_handler : the copy handler to use for cross-device copies
    """
    self.allow_xdev = allow_xdev
    self.xdev_copy_handler = xdev_copy_handler or CopyHandler()

  def copy(self, srcfile, dstfile, callback=None, size=16*1024, seek=0.0):
    # callback start
    if callback: callback._cp_start(srcfile.stat().st_size,
                                    srcfile.basename,
                                    seek=seek or 0.0)

    # perform copying
    if dstfile.exists():
      dstfile.rm()
    if not isinstance(dstfile, srcfile.__class__):
      raise SyncError("Cannot link() files across different path types")

    try:
      srcfile.link(dstfile)
    except PathError, e:
      if e.errno == 18 and self.allow_xdev:
        # tried to link across devices; copy instead
        if callback:
          if hasattr(callback, '_link_xdev'):
            callback._link_xdev(srcfile, dstfile)
        self.xdev_copy_handler.copy(srcfile, dstfile, callback=callback,
                                    size=size, seek=seek)
      else:
        raise

    # callback end
    if callback: callback._cp_end(srcfile.stat().st_size)

# convenience function
def sync(src, dst='.', strict=False, callback=None, copy_handler=None,
                       updatefn=None, allow_xdev=False,
                       xdev_copy_handler=None,
                       **kwargs):
  so = SyncOperation(strict=strict, callback=callback,
                     copy_handler=copy_handler or
                       LinkHandler(allow_xdev=allow_xdev,
                                   xdev_copy_handler=xdev_copy_handler),
                     updatefn=updatefn)
  so.sync(src, dst, **kwargs)
