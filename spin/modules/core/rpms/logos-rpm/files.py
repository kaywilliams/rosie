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

__all__ = ['FilesHandlerMixin']

try:
  import Image
  import ImageDraw
  import ImageFilter
  import ImageFont
except:
  raise ImportError("missing 'python-imaging' package")

from rendition import pps
from rendition import rxml
from rendition import versort

from spin.constants import BOOLEANS_TRUE
from spin.validate  import BaseConfigValidator

import config

XWINDOW_MAPPING = {
  'all':   ['gnome', 'kde', 'required'],
  'gnome': ['gnome', 'required'],
  'kde':   ['kde', 'required'],
  'none':  ['required'],
}

class FilesHandlerMixin(object):
  def __init__(self):
    self.fh = FilesHandlerObject(self)

class FilesHandlerObject(object):
  def __init__(self, ptr):
    self.ptr = ptr

    self._files = None
    self._schema_file = None

  @property
  def schema_file(self):
    if self._schema_file: return self._schema
    schema_file = None
    for path in self.ptr.SHARE_DIRS:
      spath = path / 'schemas/logos-rpm/config.rng'
      if spath.exists():
        schema_file = spath; break
    self._schema = schema_file
    return self._schema

  @property
  def files(self):
    if self._files: return self._files
    distroid = self.ptr.distro_info['distroid']
    c = config.ConfigletContainer()
    for path in self.ptr.SHARE_DIRS:
      cpath = path / 'logos-rpm/%s.xml' % distroid
      if not cpath.exists():
        cpath = path / 'logos-rpm/default.xml'
        if not cpath.exists():
          continue
      tree = rxml.config.read(cpath)
      self.validate_tree(tree)
      c.from_xml(tree)
    supplied = self.ptr.config.get('logos-path/text()', None)
    if supplied is not None:
      tree = rxml.config.read(supplied)
      self.validate_tree(tree)
      c.from_xml(tree)
    # get all the files, after reading all the config files, for the highest
    # precedence.
    self._files = c[self.ptr.locals.anaconda_ver]
    return self._files

  def setup(self):
    self.write_text   = self.ptr.config.get('write-text/text()', 'True') in BOOLEANS_TRUE
    required_window   = self.ptr.config.get('include-xwindows-art/text()', 'all').lower()
    self.xwindow_type = XWINDOW_MAPPING[required_window]

  def generate(self):
    for dest, info in self.files.iteritems():
      if info['xwindow-type'] not in self.xwindow_type:
        continue
      dst = self.ptr.rpm.build_folder // dest

      if info.get('source', None) is not None:
        # copy image
        src = info['source']
        self.ptr.copy(src, dst, callback=None)
      else:
        # create image
        img = Image.new('RGB', (info['width'], info['height']),
                        info.get('background', self.ptr.distro_info['background']))
        dst.dirname.mkdirs()
        img.save(dst, info.get('format', 'png'))

      if self.write_text:
        self.add_text(dst, info.get('strings', None))

  def add_text(self, image, strings):
    if strings is None:
      return
    img = Image.open(image)
    draw = ImageDraw.Draw(img)
    for i in strings:
      text_string     = i.get('text', '') % self.ptr.cvars['distro-info']
      text_coords     = (i.get('x-position', img.size[0]/2),
                         i.get('y-position', img.size[1]/2))
      text_max_width  = i.get('text-max-width', img.size[0])
      font_color      = i.get('font-color', None)
      font_size       = i.get('font-size', 52)
      font_min_size   = i.get('font-min-size', None)
      font_path       = i.get('font')
      limited_palette = i.get('limited-palette', 16)

      if font_color is None:
        if img.palette is not None:
          assert len(img.palette.palette) == (limited_palette*3)
          for i in xrange(limited_palette*3):
            if ( img.palette.palette[i] == '\xff' and
                 img.palette.palette[i+1] == '\xff' and
                 img.palette.palette[i+2] == '\xff'):
              font_color = i/3
              break
            i += 2
          assert font_color is not None, "the color 'white' not in palette of %s" % src
        else:
          font_color = 'white'

      font = ImageFont.truetype(font_path, font_size)
      w, h = draw.textsize(text_string, font=font)
      if font_min_size is not None:
        while True:
          if w <= (text_max_width or im.size[0]):
            break
          else:
            font_size -= 1
          if font_size < font_min_size:
            break
          font = ImageFont.truetype(font_path, font_size)
          w, h = draw.textsize(text_string, font=font)
      draw.text((text_coords[0]-(w/2), text_coords[1]-(h/2)),
                text_string, font=font, fill=font_color)

    del draw
    img.save(image, format=img.format)

  def validate_tree(self, tree):
    if self.schema_file is None:
      return
    validator = BaseConfigValidator([self.schema_file.dirname],
                                    tree.getroot().file)
    validator.validate('/logos-rpm', schema_file=self.schema_file.basename)
