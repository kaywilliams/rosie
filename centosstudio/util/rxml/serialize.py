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
"""
xmlserialize.py

A python serialization module for converting back and forth between python types
and XmlTrees, similar to the idea of the pickle module.

Supported types are very limited right now; see SUPPORTED_TYPES for exactly what
is currently handled.
"""

__author__  = 'Daniel Musgrave <dmusgrave@centossolutions.com>'
__version__ = '1.5'
__date__    = 'April 4th, 2008'

import types

from centosstudio.util.rxml import tree

class XmlSerializer:
  """
  Class for serializing python objects to and from an equivalent XML
  representation.

  The serialize() method accepts a python object and returns an
  XmlTreeElement that represents it.  This XmlTreeElement can be passed
  as the argument to unserialize() (see below) to get back an equivalent
  of the object originally passed in.

  The unserialize() method accepts an XmlTreeElement and returns an
  equivalent python object to the original used in serialization.
  """

  # list of (type, id) pairs; type used by serialize() to match the given
  # obj's type with a method of the name _serialize_<id>; id used by
  # unserialize to match the given tree's tag with a method of the name
  # _unserialize_<id>.  Order matters - put subclasses before their parents,
  # if the disctinction is important (as is the case with bool and int)
  SUPPORTED_TYPES = []

  def serialize(self, obj, parent=None, attrs=None):
    """
    serialized_obj = XmlSerializer.serialize(obj)

    Serializes a python object into an XmlTreeElement.  Dispatches obj
    processing to one of various obj handlers depending on its type.
    Raises a TypeError if obj is not one of the supported types (see
    SUPPORTED_TYPES, above)
    """
    for (t, id) in self.SUPPORTED_TYPES:
      if isinstance(obj, t):
        return eval('self._serialize_%s(obj, parent, attrs=attrs)' % id)
    raise TypeError("Unsupported serialization type %s" % type(obj))

  def unserialize(self, tree):
    """
    unserialized_obj = XmlUnserializer.unserialize(tree)

    Unserializes an XmlTreeElement into a python object.  Dispatches
    tree processing to one of various tree handlers depending on its
    tag.  Raises a TypeError if tree's tag is not one of the supported
    types (see SUPPORTED_TYPES, above).
    """
    if not hasattr(self, '_unserialize_%s' % tree.tag):
      raise TypeError("Unsupported unserialization type %s" % tree.tag)
    return eval('self._unserialize_%s(tree)' % tree.tag)


# SERIALIZER IMPLEMENTATIONS
class IntegerXmlSerializer(XmlSerializer):
  SUPPORTED_TYPES = [
    (types.BooleanType, 'bool'),
    (types.IntType,     'int'),
  ]

  def _serialize_bool(self, bool, parent=None, attrs=None):
    return tree.Element('bool', text=str(bool), parent=parent, attrs=attrs or {})

  def _serialize_int(self, int, parent=None, attrs=None):
    return tree.Element('int', text=str(int), parent=parent, attrs=attrs or {})

  def _unserialize_bool(self, elem):
    return elem.text == 'True'

  def _unserialize_int(self, elem):
    return int(elem.text)

class StringXmlSerializer(XmlSerializer):
  SUPPORTED_TYPES = [
    (types.StringType,  'string'),
    (types.UnicodeType, 'unicode'),
  ]

  def _serialize_string(self, string, parent=None, attrs=None):
    return tree.Element('string', text=string, parent=parent, attrs=attrs or {})

  def _serialize_unicode(self, uni, parent=None, attrs=None):
    return tree.Element('unicode', text=unicode(uni), parent=parent, attrs=attrs or {})

  def _unserialize_string(self, elem):
    return elem.text or '' # in case '' => None in the Element class

  def _unserialize_unicode(self, elem):
    return unicode(elem.text or '')

class CollectionXmlSerializer(XmlSerializer):
  SUPPORTED_TYPES = [
    (types.TupleType, 'tuple'),
    (types.ListType,  'list'),
    (set,             'set'), # no SetType in types
  ]

  def _serialize_tuple(self, t, parent=None, attrs=None):
    top = tree.Element('tuple', parent=parent, attrs=attrs or {})
    for obj in t:
      serialize(obj, parent=top)
    return top

  def _serialize_list(self, l, parent=None, attrs=None):
    top = tree.Element('list', parent=parent, attrs=attrs or {})
    for obj in l:
      serialize(obj, parent=top)
    return top

  def _serialize_set(self, s, parent=None, attrs=None):
    top = tree.Element('set', parent=parent, attrs=attrs or {})
    for obj in s:
      serialize(obj, parent=top)
    return top

  def _unserialize_tuple(self, elem):
    return tuple(self._unserialize_list(elem))

  def _unserialize_list(self, elem):
    return map(unserialize, elem.getchildren())

  def _unserialize_set(self, elem):
    return set(self._unserialize_list(elem))

class MapXmlSerializer(XmlSerializer):
  SUPPORTED_TYPES = [
    (types.DictType, 'dict'),
  ]

  def _serialize_dict(self, d, parent=None, attrs=None):
    top = tree.Element('dict', parent=parent, attrs=attrs or {})
    for key, obj in d.items():
      entry   = tree.Element('entry', parent=top)
      serialize(key, parent=tree.Element('key',   parent=entry))
      serialize(obj, parent=tree.Element('value', parent=entry))
    return top

  def _unserialize_dict(self, elem):
    d = {}
    for child in elem.getchildren():
      d[unserialize(child.get('key')[0])] = \
        unserialize(child.get('value')[0])
    return d

class NoneXmlSerializer(XmlSerializer):
  SUPPORTED_TYPES = [
    (types.NoneType, 'none')
  ]

  def _serialize_none(self, none, parent=None, attrs=None):
    return tree.Element('none', parent=parent, attrs=attrs or {})

  def _unserialize_none(self, elem):
    return None

#------ FACTORY FUNCTIONS ------#

SERIALIZERS = [
  IntegerXmlSerializer(),
  StringXmlSerializer(),
  CollectionXmlSerializer(),
  MapXmlSerializer(),
  NoneXmlSerializer(),
  XmlSerializer(),
] # add additional serializers here

def serialize(obj, parent=None, attrs=None):
  for serializer in SERIALIZERS:
    for (T,_) in serializer.SUPPORTED_TYPES:
      if isinstance(obj, T):
        return serializer.serialize(obj, parent=parent, attrs=attrs)
  raise TypeError("Unsupported serialization type %s" % type(obj))

def unserialize(tree):
  t = tree.tag
  for serializer in SERIALIZERS:
    for (_,id) in serializer.SUPPORTED_TYPES:
      if t == id:
        return serializer.unserialize(tree)
  raise TypeError("Unsupported unserialization type %s" % t)
