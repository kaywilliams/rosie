# rxml.serialize functions
from systembuilder.util.rxml import tree, serialize

from util import Token, TokenGroup, _deformat

class VersionXmlSerializer(serialize.XmlSerializer):
  SUPPORTED_TYPES = [
    (TokenGroup, 'Version'),
    (Token,      'Version'),
  ]

  def _serialize_Version(self, version, parent=None, attrs=None):
    return tree.Element('Version', text=str(version),
                        parent=parent, attrs=attrs)

  def _unserialize_Version(self, elem):
    return _deformat(elem.text, delims=['-','.'])
