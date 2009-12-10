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

from spin.validate import BaseConfigValidator

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
    self._config_files = None
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
  def config_files(self):
    if self._config_files:
      return self._config_files
    self._config_files = []

    applianceid = self.ptr.appliance_info['applianceid']

    dirs = set()
    for path in self.ptr.SHARE_DIRS:
      dirs.add(path / 'logos-rpm')
      for extra_path in path.findpaths(glob='*.pth'):
        for p in extra_path.read_lines():
          dirs.add(pps.path(p))

    for dir in dirs:
      cpath = dir / '%s.xml' % applianceid
      if not cpath.exists():
        cpath = dir / 'default.xml'

      if cpath.exists() and cpath not in self._config_files:
        self._config_files.append(cpath)

    supplied = self.ptr.config.get('logos-path/text()', None)
    if supplied is not None:
      self._config_files.append(pps.path(supplied))

    return self._config_files

  @property
  def files(self):
    if self._files:
      return self._files

    c = config.ConfigletContainer()
    for p in self.config_files:
      tree = rxml.config.read(p)
      self.validate_tree(tree)
      c.from_xml(tree)

    # get all the files, after reading all the config files, for the highest
    # precedence.
    self._files = c[self.ptr.locals.anaconda_ver]
    return self._files

  def setup(self):
    self.write_text   = self.ptr.config.getbool('write-text', 'True')
    required_window   = self.ptr.config.get('include-xwindows-art/text()', 'all').lower()
    self.xwindow_type = XWINDOW_MAPPING[required_window]

  def generate(self):
    for dest, info in self.files.iteritems():
      if info['xwindow-type'] not in self.xwindow_type:
        continue
      dst = self.ptr.rpm.source_folder // dest

      if info.get('source', None) is not None:
        # copy image
        src = info['source']
        self.ptr.copy(src, dst, callback=None)
      else:
        # create image
        img = Image.new('RGB', (info.get('width', 640), info.get('height', 480)),
                        info.get('background', self.ptr.appliance_info['background']))
        dst.dirname.mkdirs()
        img.save(dst, info.get('format', 'png'))

      if self.write_text:
        self.add_text(dst, info.get('strings', None))

  def add_text(self, image, strings):
    if not strings:
      return
    img = Image.open(image)
    draw = ImageDraw.Draw(img)
    for i in strings:
      text_string     = i.get('text', '') % self.ptr.cvars['appliance-info']
      text_coords     = (i.get('x-position', img.size[0]/2),
                         i.get('y-position', img.size[1]/2))
      text_max_width  = i.get('text-max-width', img.size[0])
      font_color      = i.get('font-color', None)
      font_size       = i.get('font-size', 52)
      font_min_size   = i.get('font-min-size', None)
      font_path       = i.get('font')
      text_alignment  = i.get('text-alignment', 'center')

      if font_color is None:
        if img.palette is not None:
          length_of_palette = len(img.palette.tostring())
          for i in xrange(length_of_palette):
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

      if text_alignment == 'center':
        text_coords = (text_coords[0]-(w/2), text_coords[1]-(h/2))
      elif text_alignment == 'right':
        text_coords = (text_coords[0]-w, text_coords[1]-(h/2))

      draw.text(text_coords, text_string, font=font, fill=font_color)

    del draw
    img.save(image, format=img.format)

  def validate_tree(self, tree):
    if self.schema_file is None:
      return
    validator = BaseConfigValidator([self.schema_file.dirname],
                                    tree)
    validator.validate('/logos-rpm', schema_file=self.schema_file.basename)
