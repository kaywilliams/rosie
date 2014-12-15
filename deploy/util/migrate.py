#!/usr/bin/python

"""
A utility for migrating definitions and template content to newer syntax.
"""

import re
import sys

from difflib import unified_diff

from deploy.util import pps
from deploy.util.listcompare import compare

ORIG = ".orig"

def migrate(command, paths, backup):
  paths = [ pps.path(x) for x in paths ] 
  
  files = []
  for p in paths:
    for f in p.findpaths(type=pps.constants.TYPE_NOT_DIR):
      if f.split('.')[-1] in ['xml', 'definition']:
        files.append(f)
 
  content = {}

  # remove XInclude namespace declaration
  for f in files: 
    oldlines = content.get(f, f.read_lines())
    newlines = []

    # do single-line operations 
    for l in oldlines:
      l = remove_namespace(l)
      l = remove_tag_prefix(l)
      l = convert_xpointer_attr(l)
      l = convert_single_line_xpointer_content(l)
      newlines.append(l)

    # do multi-line operations
    newlines = convert_multi_line_xpointer_content(newlines)
    newlines = align_include_attributes(newlines)
    newlines = align_at_symbols_in_multi_line_xpath_attributes(newlines)

    content[f] = (oldlines, newlines)

  modified = sorted([ f for f,v in content.items() if v[0] != v[1] ])

  if command == 'diff':
    diff(modified, content)

  if command == 'status':
    print '\n'.join(modified)

  if command == 'commit':
    commit(modified, content, backup)

def remove_namespace(l):
  return re.sub(r' xmlns:xi=\'http://www.w3.org/2001/XInclude\'', '', l)

def remove_tag_prefix(l):
  return re.sub(r'<xi:include', '<include', l)

def convert_xpointer_attr(l):
  return re.sub(r'xpointer=', 'xpath=', l)

def convert_single_line_xpointer_content(l):
  return re.sub(r'(["\'])xpointer\((.*)\)(["\'])', r'\1\2\3', l)

def convert_multi_line_xpointer_content(lines):
  newlines = []
  sublines = []
  for l in lines:
    if 'xpointer(' in l:
      sublines.append(l.replace('xpointer(', ''))
    else:
      if sublines:
        if re.search(r'\)["\']', l):
          sublines.append(re.sub(r'\)(["\'])', r'\1', l))
          newlines.extend(sublines)
          sublines = []
        else:
          sublines.append(l)
      else:
        newlines.append(l)

  return newlines

def align_include_attributes(lines):
  newlines = []
  sublines = []
  index = None 
  for l in lines:
    if index:
      l = re.sub(r'^[\s]*xpath', ' ' * index + 'xpath', l)
      l = re.sub(r'^[\s]*parse', ' ' * index + 'parse', l)
      newlines.append(l)
      index = None
    else:
      newlines.append(l)
      if 'include href' in l and not '>' in l:
        index = l.find('href')

  return newlines

def align_at_symbols_in_multi_line_xpath_attributes(lines):
  newlines = []
  sublines = []
  index = None
  for l in lines:
    if re.match(r'^[\s]*xpath=', l) and '@' in l and not '>' in l:
      sublines = [l]
      index = l.index('@')
    else:
      if sublines:
        if '@' in l:
          l = re.sub(r'^[\s]*', ' ' * index, l)
          sublines.append(l)
        else:
          newlines.extend(sublines)
          sublines = []
          newlines.append(l)
      else:
        newlines.append(l)

  return newlines
  
def diff(modified, content):
  for f in modified:
    old, new = content[f]
    for line in unified_diff(old, new, fromfile=f+ORIG, tofile=f, lineterm=""):
      print line

def commit(modified, content, backup):
  for f in modified:
    if backup:
      print "writing", f+ORIG
      f.move(f+ORIG)
    print "writing", f
    f.write_lines(content[f][1])

##### main #####
if __name__ == "__main__":
  commands = ['diff', 'status', 'commit']
  backup = True

  usage = "usage: migrate.py [%s] path+" % '|'.join(commands)

  if len(sys.argv) < 3:
    print usage
    sys.exit(1)

  if sys.argv[1] not in commands:
    print usage
    sys.exit(1)

  nb = "--no-backup"
  if nb in sys.argv:
    sys.argv.remove(nb)
    backup = False

  migrate(sys.argv[1], sys.argv[2:], backup)
