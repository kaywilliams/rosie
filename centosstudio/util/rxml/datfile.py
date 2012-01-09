#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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

from centosstudio.util import pps
from centosstudio.util.rxml import config, tree

class DatfileElement(config.ConfigElement):
  "An element in a Datfile XML tree."

  def write(self):
    datfn = self.file
    configfn = datfn[:-len('.dat')]

    config.ConfigElement.write(self, datfn)

    if configfn.exists():
      # set the mode and ownership of .dat file to match basefile.
      st = configfn.stat()
      datfn.chown(st.st_uid, st.st_gid)
      datfn.chmod(st.st_mode)

class DatfileTreeSaxHandler(config.ConfigTreeSaxHandler):
  def __init__(self, makeelement=None):
    config.ConfigTreeSaxHandler.__init__(self, makeelement=makeelement)

#--------FACTORY FUNCTIONS--------#
PARSER = lxml.etree.XMLParser(remove_blank_text=False, remove_comments=True)
PARSER.setElementClassLookup(lxml.etree.ElementDefaultClassLookup(
                             element=DatfileElement, 
                             comment=tree.XmlTreeComment))

def Element(name, parent=None, text=None, attrs=None, parser=PARSER, **kwargs):
  t = tree.Element(name, parent=parent, text=text, attrs=attrs,
                         parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def uElement(name, parent, text=None, attrs=None, parser=PARSER, **kwargs):
  t = tree.uElement(name, parent=parent, text=text, attrs=attrs,
                           parser=parser, **kwargs)
  if text is None: t.text = None
  return t

def parse(basefile, handler=None, parser=PARSER):
  """Accepts a base filename and parses a corresponding '.dat' file, creating
the datfile if necessary"""

  pps.path(basefile)
  datfn = (basefile.dirname / basefile.basename + '.dat')
  datfn.dirname.mkdirs()

  if datfn.exists():
    datfile = tree.parse(datfn,
                       handler or DatfileTreeSaxHandler(parser.makeelement),
                       parser=parser).getroot()

  else:
    datfile = Element('data')

  datfile.file = datfn

  return datfile

