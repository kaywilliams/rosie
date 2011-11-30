#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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

import lxml

from centosstudio.util import rxml

class DatfileMixin:
  def __init__(self):
    self.datfn = (self._config.getpath(
                        '/solution/config/@datafile-dir', 
                        self._config.file.dirname) / 
                        self._config.file.basename + '.dat')
    self.datfn.dirname.mkdirs()

    if self.datfn.exists():
      self.datfile = parse(self.datfn).getroot().get('/solution')
    else:
      self.datfile = Element('solution')


class DatfileElement(rxml.config.ConfigElement):
  "An element in a Datfile XML tree."

  def write(self, datfn, configfn):
    rxml.config.ConfigElement.write(self, datfn)

    if configfn.exists():
      # set the mode and ownership of .dat file to match definition file.
      st = configfn.stat()
      datfn.chown(st.st_uid, st.st_gid)
      datfn.chmod(st.st_mode)

class DatfileTreeSaxHandler(rxml.config.ConfigTreeSaxHandler):
  def __init__(self, makeelement=None):
    rxml.config.ConfigTreeSaxHandler.__init__(self, makeelement=makeelement)

#--------FACTORY FUNCTIONS--------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=True)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(
                             element=DatfileElement, 
                             comment=rxml.tree.XmlTreeComment))

def Element(name, parent=None, text=None, attrs=None, parser=PARSER, **kwargs):
  t = rxml.tree.Element(name, parent=parent, text=text, attrs=attrs,
                         parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def uElement(name, parent, text=None, attrs=None, parser=PARSER, **kwargs):
  t =  rxml.tree.uElement(name, parent=parent, text=text, attrs=attrs,
                           parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def parse(file, handler=None, parser=PARSER):
  datfile = rxml.tree.parse(file,
                       handler or DatfileTreeSaxHandler(parser.makeelement),
                       parser=parser)
  return datfile

