#
# Copyright (c) 2013
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

import lxml

from deploy.util import pps
from deploy.util.rxml import config, tree

# TODO - eliminate this module and move remaining custom logic into deploy
# event/__init__ module.
class DatfileElement(config.ConfigElement): pass

class DatfileTreeSaxHandler(config.ConfigTreeSaxHandler):
  def __init__(self, makeelement=None):
    config.ConfigTreeSaxHandler.__init__(self, makeelement=makeelement)

#--------FACTORY FUNCTIONS--------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=True)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(
                             element=DatfileElement, 
                             comment=tree.XmlTreeComment))

def Element(name, parent=None, text=None, attrib=None, parser=PARSER, **kwargs):
  t = config.Element(name, parent=parent, text=text, attrib=attrib,
                         parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def uElement(name, parent, text=None, attrib=None, parser=PARSER, **kwargs):
  t = config.uElement(name, parent=parent, text=text, attrib=attrib,
                           parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def parse(file, handler=None, parser=PARSER):
  """Accepts a filename and parses the file, creating it if necessary"""

  file = pps.path(file)
  file.dirname.mkdirs()

  if file.exists():
    datfile = config.parse(file, 
                     handler or DatfileTreeSaxHandler(parser.makeelement),
                     parser=parser).getroot()

  else:
    datfile = Element('data')

  datfile.file = file

  return datfile

