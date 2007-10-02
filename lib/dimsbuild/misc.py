from StringIO import StringIO

from dims import xmllib

def locals_imerge(string, ver):
  tree = xmllib.tree.read(StringIO(string))
  locals = xmllib.tree.Element('locals')
  for child in tree.getroot().getchildren():
    locals.append(xmllib.imerge.incremental_merge(child, ver))
  return locals

def locals_printf(elem, vars):
  string = elem.get('string-format/@string', elem.text)
  format = elem.xpath('string-format/format/item/text()')
  return printf(string, format, vars)

def printf(string, fmt, vars):
  for f in fmt:
    try:
      string = string.replace('%s', vars[f], 1)
    except KeyError:
      raise KeyError, "Variable '%s' not defined in supplied scope" % f
  return string
