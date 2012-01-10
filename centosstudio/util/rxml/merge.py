#
# Copyright (c) 2012
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
"""
xmlmerge.py

Library for converting an XML document into a nested dictionary.  Also
supports merging of multiple XML documents into a single XML
Dictionary.

XML documents under this scheme perform 'actions' on the existing XML
dictionary.  These actions can be one of 'insert', 'delete', 'chmod',
and 'replace', which add a new node, delete an existing node, change
the permissions on an existing node, or replace an existing node with
a new one, respectively.

Before performing an action, the node itself is checked to see if it
has the correct permissions.  Permissions are denoted by the
'allowoverride' attribute in itself or one of its parent.  Actions are
only performed if the node in question has the correct permissions (or
if secure mode is enabled, see below).

There exist two functions for performing this merge: SecureXmlMerge()
and XmlMerge().  Both functions perform the same task; however,
SecureXmlMerge overrides the ACL modes of the XML dictionary (meaning,
basically, that is is unaffected by permissions), while XmlMerge obeys
them.  The intent of this functionality is to provide an interface
which allows trusted code to use the unconstrained interface
(SecureXmlMerge) while still allowing untrusted code to operate within
a confined domain (XmlMerge).
"""

__author__  = "Daniel Musgrave <dmusgrave@centosstudio.org>"
__version__ = "2.0"
__date__    = "Janary 25, 2007"

import copy
import re
import sys

from centosstudio.util.rxml import tree

BOOLEANS = {
  'yes': True,  'Yes': True,  'true':  True,  'True':  True,  '1': True,
  'no':  False, 'No':  False, 'false': False, 'False': False, '0': False,
}

NSMAP = {'xm': 'http://www.centosstudio.org/ns/merge'}

class XmlMergeHandler:
  """
  Handler class responsible for merging an XML tree with another XML
  tree.

  Expects the following syntax in merge files:
  < <documentroot> >
    <action type="<type>" path="<path>" <other args> >
      < <subelements> />
    </action>
    <action .../>
    ...
  </ <documentroot> >

  <documentroot> should match the document root of the tree being
  merged into.  Beneath the root, there should be a list of actions to
  perform on the main tree; the actual action to perform is specified
  by the '<type>' attribute.

  The following actions are supported:
    * insert:  insert one or more nodes in one or more locations
    * delete:  delete one or more nodes from one or more locations
    * chmod:   create or modify the 'allowoverride' attribute of one or
               more nodes
    * replace: replace the contents of one or more nodes
    * update:  recursively update the contents of one or more nodes

  Actions are performed on nodes that match the XPath expression
  contained in <path>.  If this query results in multiple elements,
  then the action is applied equally to all of them, so it is
  important that <path> be specific enough to apply to only those
  nodes that should be affected.

  Actions obey a set of permissions inherited from the target
  element's parents or specified directly in the 'allowoverride'
  attribute.  When not in secure mode, an action will only be
  performed if the effective permissions for the target node are
  'yes'.  In secure mode, nodes, can be modified regardless of the
  effective element permissions.
  """

  def __init__(self, tree=None, secure=False, allowoverride="yes"):

    self.actions = { # mapping of allowable 'type' attrs to functions
      "insert":  self._insert_element,
      "delete":  self._delete_element,
      "chmod":   self._chmod_element,
      "update":  self._update_element,
      "replace": self._replace_element,
    }

    if allowoverride in BOOLEANS:
      override = BOOLEANS[allowoverride]
    else:
      raise ValueError("Invalid allowoverride '%s'; must be one of %s" % (allowoverride,BOOLEANS.keys()))

    if tree is not None:
      self.tree = tree
      self.root = tree.getroot()
    else:
      self.tree = None
      self.root = None
    self.override_default = allowoverride # save this for later use
    self.content = re.compile("[\w]+") # RE for finding strings with at least one nonwhitespace char
    self.securemode = secure  # whether we're operating in secure (admin) mode

  def mergefile(self, file):
    "Merge the contents of file with self.tree"
    return self.merge(tree.parse(file)).getroot()

  def merge(self, mergetree):
    "Merge the contents of tree with self.tree"
    # get the list of actions to perform
    actions = mergetree.getroot().xpath('xm:action', namespaces=NSMAP)
    if len(actions) == 0:
      if self.tree is None:
        # this is a special case - if self.tree isn't yet populated, then we'll
        # accept a standard XML file that doesn't follow our special syntax -
        # essentially, this is the 'base' file that will be modified by other merge
        # files
        self.tree = mergetree
        self.root = self.tree.getroot()
        return
      else:
        # if self.tree is already populated, all subsequent merge files must match
        # the special syntax
        raise InvalidXmlContentError("Missing <action> node(s) in merge "
                                     "file '%s'" % file)

    # make sure root tags match
    if mergetree.getroot().tag != _CN('xm:merge'):
      raise InvalidXmlContentError("Root element of merge document not valid for merging")

    # perform actions
    for action in actions:
      name = self._get_attrib(action, 'xm:type')

      if name not in self.actions.keys():
        raise InvalidXmlContentError("Invalid action type '%s' specified in "
                                     "the following action:\n%s" % (name, action))

      path = self._get_attrib(action, 'xm:path')
      elements = self.root.xpath(path)
      if len(elements) == 0:
        raise InvalidXmlContentError("The specified path, '%s', matched no "
                                     "nodes in the main document" % path)

      for element in elements:
        if self.check_permissions(element):
          self.actions[name](element, action)
        else:
          raise XmlPermissionDeniedError("Permission to modify node '%s' "
                                         "denied" % element.tag)


  #------ UTILITY METHODS ------#
  def _get_attrib(self, action, attr):
    """
    Get an attribute from an action.  Raises InvalidXmlContentError if
    such an attribute doesn't exist
    """
    try:
      return action.attrib[_CN(attr)]
    except KeyError, e:
      raise InvalidXmlContentError("Missing '%s' attribute in the following "
                                   "action:\n%s" % (e.args[0], action))

  def check_permissions(self, node):
    """
    Check the permissions of node by looking for an 'allowoverride'
    attribute.  If the node doesn't contain one, check its parent.  If
    never specified, assume True.
    """
    allowoverride = node.attrib.get(_CN('xm:allowoverride'), None)
    if allowoverride is not None:
      if self.securemode or BOOLEANS[allowoverride]:
        return True
      else:
        return False
    else:
      try:
        return self.check_permissions(node.getparent())
      except AttributeError, e:
        return True # assuming permissions ok if not otherwise specified

  #------ ACTION METHODS ------#

  def _insert_element(self, element, action):
    """
    Indexing works as follows:
      index >= len(children)      : insert after elem[-1]
      len(children) > index >= 0  : insert before elem[index]
      0 > index >= -len(children) : insert after elem[len(children)+index]
      -len(children) > index      : insert before elem[0]

    This makes sense in practice (trust me!); see following diagram

    For example, in the following tree (comments indicate location for an insert
    with the given index)

      <root>
        <!-- index 0, -4 and lower -->
        <a1/>
        <!-- index 1, -3 -->
        <a2/>
        <!-- index 2, -2 -->
        <a3/>
        <!-- index 3 and higher, -1 -->
      </root>

    the following indicies give the following results:
      5: insert <elem> after <a3> (5 > 3, so -1)
      2: insert <elem> before <a3> (2)
      1: insert <elem> before <a2> (1)
      0: insert <elem> before <a1> (0)
      -1: insert <elem> after <a3> (3 + -1 = 2)
      -2: insert <elem> after <a2> (3 + -2 = 1)
      -5: insert <elem> before <a1> (3 + -5 = -2, cap to 0)
    """
    max_pos = len(element.getchildren())

    position = action.attrib.get(_CN('xm:position'), '-1')
    position = int(position)

    fn = tree.XmlTreeElement.addprevious

    # indexed from right side of array instead of left
    if position < 0:
      position = max_pos + position
      fn = tree.XmlTreeElement.addnext

    # cap index to 0 and max_pos - 1
    if position < 0:
      position = 0
      fn = tree.XmlTreeElement.addprevious
    elif position >= max_pos:
      position = max_pos - 1
      fn = tree.XmlTreeElement.addnext

    unique = BOOLEANS[action.attrib.get(_CN('xm:unique'), 'false')]

    for child in reversed(action.getchildren()):
      if unique and element.get(child.tag) is not None:
        continue
      fn(element[position], copy.deepcopy(child))

  def _delete_element(self, element, action):
    element.getparent().remove(element)

  def _chmod_element(self, element, action):
    if not self.securemode: # not allowed to modify node permissions in nonsecure mode
      raise XmlPermissionDeniedError("Permission to modify node denied")
    element.attrib[_CN('xm:allowoverride')] = self._get_attrib(action, 'xm:value')

  def _update_element(self, element, action):
    for k,v in action.attrib.items():
      if not k.startswith(_CN('xm:')): # not in our namespace
        element.attrib[k] = v
    if action.text:
      element.text = action.text

  def _replace_element(self, element, action):
    parent = element.getparent()
    index = parent.index(element)
    parent.remove(element)
    for elem in reversed(copy.deepcopy(action.getchildren())):
      parent.insert(index, elem)


#------ MERGE METHODS ------#
def SecureXmlMerge(tree, file):
  "Secure merge function; causes XML merging to ignore ACL modes."
  handler = XmlMergeHandler(tree=tree, secure=True)
  handler.mergefile(file)
  return handler.tree

def XmlMerge(tree, file):
  "Default (insecure) merge function; XML merging obeys ACL modes."
  handler = XmlMergeHandler(tree=tree)
  handler.mergefile(file)
  return handler.tree


def _CN(name):
  "convert <prefix>:<name> to {namespace}name"
  if ':' in name:
    prefix, name = name.split(':', 1)
    return '{%s}%s' % (NSMAP[prefix], name)
  else:
    return name


#------ ERRORS ------#
class InvalidXmlContentError(Exception):
  "Exception raised when an XML document doesn't match the required DTD."

class XmlPermissionDeniedError(Exception):
  """
  Exception raised when an XML document tries to modify something it
  doesn't have permissions for.
  """

#------ TESTING ------#
if __name__ == "__main__":
  # simple default main function - merges all arguments on command line together,
  # treating the first like an admin config file and the rest like user configs.
  # This is meant more for testing than actual use
  handler = XmlMergeHandler()
  args = sys.argv[1:]
  if len(args) < 1:
    print "too few args"
    sys.exit(1)
  mergedOutput = SecureXmlMerge(None, args[0])
  for i in range(1, len(args)):
    mergedOutput = XmlMerge(mergedOutput, args[i])
  print "----"
  print mergedOutput
  print "----"
