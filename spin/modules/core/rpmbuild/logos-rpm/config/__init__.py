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
__all__ = ['RecursiveUpdateDict', 'ConfigletContainer']

from rendition import versort
from rendition import pps

import configlets

class RecursiveUpdateDict(dict):
  def __init__(self, *args, **kwargs):
    dict.__init__(self, *args, **kwargs)

  def __getitem__(self, key):
    ret = {}
    for index in versort.sort(self.keys()):
      val = dict.__getitem__(self, str(index))
      if index <= key:
        ret = self.rupdate(dict.__getitem__(self, str(index)), ret)
    return ret

  def rupdate(self, src, dst):
    for k,v in src.items():
      if isinstance(v, dict):
        rdst = dst.setdefault(k, {})
        self.rupdate(v, rdst)
      else:
        dst[k] = v
    return dst


class ConfigletContainer(RecursiveUpdateDict):
  def __init__(self, *args, **kwargs):
    RecursiveUpdateDict.__init__(self, *args, **kwargs)

  def rupdate(self, src, dst):
    for k,v in src.items():
      if isinstance(v, configlets.RemoveConfiglet):
        if k in dst: del(dst[k])
      elif isinstance(v, configlets.Configlet):
        if k in dst and dst[k].precedence <= v.precedence:
          dst[k].update(v)
        else:
          dst[k] = v
    return dst

  def from_xml(self, element):
    defaults = {}
    for default in ['width', 'height', 'background', 'format', 'font']:
      value = element.get('defaults/%s/text()' % default, None)
      if value is None:
        continue
      if default == 'font':
        value = pps.path(element.getroot().file).dirname / value
      if default == 'width' or default == 'height':
        value = int(value)
      defaults[default] = value

    precedence = element.get('precedence/text()', '1')
    parent_dir = element.getroot().file.dirname
    for file in element.xpath('file|image', []):
      dst = file.get('@dest')
      anc = 'anaconda-%s' % file.get('@anaconda-version', '0')
      obj = configlets.configlet(file, parent_dir, precedence, defaults)
      pdict = self.setdefault(anc, {})
      if dst not in pdict or pdict[dst].precedence <= obj.precedence:
        pdict.update({dst: obj})

