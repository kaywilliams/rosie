#
# Copyright (c) 2012
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
import imp
import os

from deploy.util import pps
from deploy.util import shlib

from errors import *

#------ GLOBAL VARS ------#
IMGLIB_TEMP = pps.path('/tmp/imglib')
IMGLIB_MNT  = IMGLIB_TEMP / 'mnt'

# dictionary of handler names and their associated req'd packages
HANDLERS = ['gzip']

MODE_READ = 'r'
MODE_WRITE = 'w'
MODES = [MODE_READ, MODE_WRITE]

IMAGE_FORMATS = {} # not currently used
NEW_IMAGE_FACTORY = {}


#---------FACTORY FUNCTIONS---------#
def MakeImage(file, format, zipped=False, zip_format='gzip', **kwargs):
  if format not in IMAGE_FORMATS:
    raise ValueError("Image format '%s' not supported; must be one of %s" % \
                      (format, IMAGE_FORMATS))

  file = pps.path(file)
  ex = file.exists()
  img = NEW_IMAGE_FACTORY[format](file, zipped=zipped, zip_format=zip_format,
                                  **kwargs)

  # not clear why we're zipping a file that doesn't exist
  if not ex and zipped:
    if zip_format == 'gzip':
      shlib.execute('/usr/bin/gzip %s' % file)
      file.rename('%s.gz' % file)
    if zip_format == 'lzma':
      shlib.execute('/usr/bin/xz -9 --format=lzma %s' % file)
      file.rename('%s.lzma' % file)

  return img


#------ UTILITY FUNCTIONS ------#
def process_module(module):
  "Populate factory function global lists"
  if not hasattr(module, 'IMAGES'): return
  for image in module.IMAGES:
    # rpm checking here
    for alias in image['aliases']:
      IMAGE_FORMATS[alias] = getattr(module, image['class'])
      NEW_IMAGE_FACTORY[alias] = getattr(module, image['factory'])

def acquire_mount_point():
  "Returns earliest available mount point"
  index = 0
  while (IMGLIB_MNT/str(index)).exists():
    index += 1
  point = IMGLIB_MNT/str(index)
  point.mkdirs()
  return point

def release_mount_point(p):
  "Release a mount point back into the pool to be used again"
  p.rm(recursive=True, force=True)

def cleanup():
  "Cleanup any orphaned mounts and remove the temporary directory"
  for mount in IMGLIB_MNT.findpaths(mindepth=1):
    if mount in pps.path('/proc/mounts').read_text():
      shlib.execute('/bin/umount %s' % mount)

  IMGLIB_TEMP.rm(recursive=True, force=True)


# load handler modules
for modfile in (pps.path(__path__[0])/'modules').findpaths(glob='*.py',
    type=pps.constants.TYPE_NOT_DIR, mindepth=1, maxdepth=1):

  modname = 'img-'+modfile.basename.splitext()[0]
  process_module(imp.load_source(modname, modfile))
