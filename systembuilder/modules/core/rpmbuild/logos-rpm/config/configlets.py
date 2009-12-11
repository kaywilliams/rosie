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
from rendition import pps
from rendition import versort

from systembuilder.errors import SpinError

class Configlet(dict):
  def __init__(self, element, parent_dir, precedence, **kwargs):
    self.element    = element
    self.parent_dir = parent_dir
    self.precedence = versort.Version(precedence)

    kwargs.update({'xwindow-type' : element.get('@xwindow-type', 'required')})
    dict.__init__(self, **kwargs)


class ImageConfiglet(Configlet):
  def __init__(self, element, parent_dir, precedence, **kwargs):
    Configlet.__init__(self, element, parent_dir, precedence, **kwargs)

  def read(self):
    strings = []
    for elem in self.element.xpath('string', []):
      text_info = {}
      for child in ['font', 'font-min-size', 'font-size', 'text',
                    'text-max-width', 'x-position', 'y-position',
                    'text-alignment']:
        value = elem.get('%s/text()' % child, None)
        if value is not None: text_info[child] = value
      if text_info.get('text', None) is not None:
        text_info['text'] = text_info['text'].replace('%{', '%(').replace('}', ')s')

      for toint in ['font-min-size', 'font-size', 'text-max-width',
                    'x-position', 'y-position']:
        if text_info.get(toint, None) is not None:
          text_info[toint] = int(text_info[toint])
      font = text_info.get('font', self.get('font', None))
      if font is not None:
        text_info['font'] = self.parent_dir / font
      else:
        raise FontNotDefinedError(elem.sourceline, self.element.getroot().file)
      strings.append(text_info)
    self['strings'] = strings

class CopyConfiglet(Configlet):
  def __init__(self, element, parent_dir, precedence, **kwargs):
    kwargs.update({'source': parent_dir / element.get('path/text()')})
    Configlet.__init__(self, element, parent_dir, precedence, **kwargs)

class RemoveConfiglet(Configlet):
  def __init__(self, element, parent_dir, precedence, **kwargs):
    kwargs.update({'remove': True})
    Configlet.__init__(self, element, parent_dir, precedence, **kwargs)

class CreateImageConfiglet(ImageConfiglet):
  def __init__(self, element, parent_dir, precedence, **kwargs):
    ImageConfiglet.__init__(self, element, parent_dir, precedence, **kwargs)

  def read(self):
    ImageConfiglet.read(self)
    for child in ['width', 'height', 'background', 'format']:
      value = self.element.get('create/%s/text()' % child, None)
      if value is not None:
        self[child] = value
      if self.get('width', None) is not None:
        self['width'] = int(self['width'])
      if self.get('height', None) is not None:
        self['height'] = int(self['height'])

class CopyImageConfiglet(ImageConfiglet):
  def __init__(self, element, parent_dir, precedence, **kwargs):
    ImageConfiglet.__init__(self, element, parent_dir, precedence, **kwargs)

  def read(self):
    ImageConfiglet.read(self)
    self['source'] = self.parent_dir / self.element.get('source/text()')

registered_configlets = {}
def register_configlet(tag, child_name, cls):
  registered_configlets.setdefault(tag, {}).update({child_name: cls})

def configlet(element, parent_dir, precedence, defaults):
  tag = element.tag
  try:
    for path in registered_configlets[tag].iterkeys():
      if element.pathexists(path):
        obj = registered_configlets[tag][path](element, parent_dir, precedence, **defaults)
        if hasattr(obj, 'read') and callable(getattr(obj, 'read')):
          obj.read()
        return obj
    raise UnknownConfigletError()
  except (KeyError, UnknownConfigletError), e:
    raise UnknownConfigletError(element, element.getroot().file)

register_configlet('file',  'path',   CopyConfiglet)
register_configlet('file',  'remove', RemoveConfiglet)
register_configlet('image', 'create', CreateImageConfiglet)
register_configlet('image', 'remove', RemoveConfiglet)
register_configlet('image', 'source', CopyImageConfiglet)

class UnknownConfigletError(SpinError):
  message = "Config element not recognized\n%(element)sin file: %(file)s"
class FontNotDefinedError(SpinError):
  message = "No font file specified to write text with in the <string> element "\
      "(line %(lineno)s, file '%(file)s'). You can resolve the error by adding a "\
      "<font> element in the <defaults> or the <string> element."
