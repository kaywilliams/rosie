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
try:
  import Image
  import ImageDraw
  import ImageFilter
  import ImageFont
except:
    raise ImportError("missing 'python-imaging' module")

from rendition import pps

from gradient import ImageGradient

__all__ = [
  'CommonFilesHandler',
  'DistroFilesHandler',
  'SuppliedFilesHandler',
]

class LogosRpmFilesHandler(object):
  def __init__(self, ptr, paths, write_text=False):
    self.ptr = ptr
    self.paths = paths
    self.write_text = write_text

  def generate(self):
    for path in self.paths:
      for src in path.findpaths(type=pps.constants.TYPE_NOT_DIR):
        id  = pps.path('/') // src.relpathfrom(path)
        if not self._check_id(id): continue
        dst = self.ptr.build_folder // src.relpathfrom(path)
        self._generate_file(src, dst)
        if ( self.write_text and
             self.ptr.locals.L_LOGOS_RPM_FILES.has_key(id) ):
          self._add_text(id, dst)

  def _generate_file(self, id, src, dst):
    raise NotImplementedError()

  def _check_id(self, id):
    return True

  def _add_text(self, id, file):
    if not id in self.ptr.locals.L_LOGOS_RPM_FILES:
      return
    strings = self.ptr.locals.L_LOGOS_RPM_FILES[id].get('strings', None)
    if strings is None:
      return
    src = self.ptr.build_folder // id
    img = Image.open(src)
    draw = ImageDraw.Draw(img)
    for i in strings:
      text_string     = i.get('text', '') % self.ptr.cvars['distro-info']
      halign          = i.get('halign', 'center')
      text_coords     = i.get('text_coords', (img.size[0]/2, img.size[1]/2))
      text_max_width  = i.get('text_max_width', img.size[0])
      font_color      = i.get('font_color', None)
      font_size       = i.get('font_size', 52)
      font_size_min   = i.get('font_size_min', None)
      font_face       = i.get('font', 'DejaVuLGCSans.ttf')
      limited_palette = i.get('limited_palette', 16)

      if font_face not in self.fonts:
        continue
      else:
        font_path = self.fonts[font_face]

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
      if font_size_min is not None:
        while True:
          if w <= (text_max_width or im.size[0]):
            break
          else:
            font_size -= 1
          if font_size < font_size_min:
            break
          font = ImageFont.truetype(font_path, font_size)
          w, h = draw.textsize(text_string, font=font)

      if halign == 'center':
        draw.text((text_coords[0]-(w/2), text_coords[1]-(h/2)),
                  text_string, font=font, fill=font_color)
      elif halign == 'right':
        draw.text((text_coords[0]-w, text_coords[1]-(h/2)),
                  text_string, font=font, fill=font_color)

    del draw
    img.save(src, format=img.format)

  def _get_fonts(self):
    if hasattr(self, '_fonts'):
      return self._fonts
    self._fonts = {}
    for path in self.ptr.SHARE_DIRS:
      fonts = (path / 'logos-rpm/fonts').findpaths()
      for font in fonts:
        self._fonts[font.basename] = font
    return self._fonts
  fonts = property(_get_fonts)


class SuppliedFilesHandler(LogosRpmFilesHandler):
  def __init__(self, ptr, paths, write_text):
    LogosRpmFilesHandler.__init__(self, ptr, paths, write_text=write_text)

  def _generate_file(self, src, dst):
    dst.dirname.mkdirs()
    self.ptr.copy(src, dst.dirname, callback=None)


class CommonFilesHandler(LogosRpmFilesHandler):
  def __init__(self, ptr, paths):
    LogosRpmFilesHandler.__init__(self, ptr, paths)

  def _generate_file(self, src, dst):
    if dst.exists(): return
    dst.dirname.mkdirs()
    self.ptr.copy(src, dst.dirname, callback=None)


class DistroFilesHandler(LogosRpmFilesHandler):
  def __init__(self, ptr, paths, write_text, xwindow_types, start_color, end_color):
    LogosRpmFilesHandler.__init__(self, ptr, paths, write_text=write_text)
    self.xwindow_types = xwindow_types
    self.start_color   = start_color
    self.end_color     = end_color

  def generate(self):
    if self.paths: LogosRpmFilesHandler.generate(self)
    for id in self.ptr.locals.L_LOGOS_RPM_FILES:
      file = self.ptr.build_folder // id
      xwt = self.ptr.locals.L_LOGOS_RPM_FILES[id]['xwindow_type']
      if not file.exists() and xwt in self.xwindow_types:
        # generate image because not found in any shared folder
        width  = self.ptr.locals.L_LOGOS_RPM_FILES[id]['image_width']
        height = self.ptr.locals.L_LOGOS_RPM_FILES[id]['image_height']
        format = self.ptr.locals.L_LOGOS_RPM_FILES[id].get('image_format', 'PNG')

        img = Image.new('RGBA', (width, height))
        grd = ImageGradient(img)
        grd.draw_gradient(self.start_color, self.end_color)
        file.dirname.mkdirs()
        img.save(file, format=format)

        if self.write_text: self._add_text(id, file)

  def _check_id(self, id):
    if not self.ptr.locals.L_LOGOS_RPM_FILES.has_key(id): return False
    xwt = self.ptr.locals.L_LOGOS_RPM_FILES[id].get('xwindow_type', 'required')
    return xwt in self.xwindow_types

  def _generate_file(self, src, dst):
    if dst.exists(): return
    dst.dirname.mkdirs()
    self.ptr.copy(src, dst.dirname, callback=None)
