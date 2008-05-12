#!/usr/bin/python
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

import optparse
import sys
import unittest

from rendition import pps

from rendition.CleanHelpFormatter import CleanHelpFormatter

opt_defaults = dict(
  logthresh = 0,
  logfile = None,
  libpath   = [],
  sharepath = [],
  force_modules = [],
  skip_modules  = [],
  force_events  = [],
  skip_events   = [],
  skip_test = [],        # new
  mainconfigpath = None, # new
  enabled_modules  = [],
  disabled_modules = [],
  list_events = False,
  no_validate = True,
  clear_cache = False,
)
test_options = None # set on running parse_cmd_args(), below


LOGFILE = open('test.log', 'w+')

def make_logger(threshold):
  console = logger.Logger(threshold=threshold, file_object=sys.stdout)
  logfile = logger.Logger(threshold=threshold, file_object=LOGFILE)
  return spintest.EventTestLogContainer([console, logfile])

def parse_cmd_args():
  parser = optparse.OptionParser("usage: %prog [OPTIONS]",
                                 formatter=CleanHelpFormatter())

  parser.add_option('-d', '--base-distro', metavar='DISTRO',
    dest='basedistro',
    default='fedora-6',
    help='select the distribution to test')
  parser.add_option('-a', '--base-arch', metavar='ARCH',
    dest='basearch',
    default='i386',
    help='select the arch of the distribution to test')
  parser.add_option('-b', '--build-root', metavar='DIRECTORY',
    dest='buildroot',
    default='/tmp/spintest',
    help='choose the location where builds should be performed')
  parser.add_option('--skip', metavar='MODULEID',
    dest='skip_test',
    action='append',
    help='skip testing of a certain event, by id')
  parser.add_option('--spin-conf', metavar='PATH',
    dest='mainconfigpath',
    help='specify path to a main config file')
  parser.add_option('--lib-path', metavar='PATH',
    dest='libpath',
    action='append',
    help='specify directory containing spin library files')
  parser.add_option('--share-path', metavar='PATH',
    dest='sharepath',
    action='append',
    help='specify directory containing spin share files')
  parser.add_option('-l', '--log-level', metavar='N',
    default=2,
    type='int',
    dest='testloglevel',
    help='specify the level of verbosity of the output log')
  parser.add_option('--no-clear-cache',
    dest='clear_test_cache',
    default=True,
    action='store_false',
    help='don\'t clear event cache when done testing')

  parser.set_defaults(**opt_defaults)

  return parser.parse_args(sys.argv[1:])

def main():
  import imp

  options, args = parse_cmd_args()

  sys.path = options.libpath + sys.path

  import spintest

  spintest.BUILD_ROOT = pps.path(options.buildroot)
  spintest.EventTestCase.options = options

  runner = spintest.EventTestRunner(options.testloglevel)
  suite = unittest.TestSuite()

  if not args:
    args = [ pps.path(__file__).abspath().dirname/'__init__.py' ]
  for arg in args:
    testpath = _testpath_normalize(arg)
    fp = None
    try:
      fp,p,d = imp.find_module(testpath.basename, [testpath.dirname])
      mod = imp.load_module('test-%s' % testpath.dirname.basename, fp, p, d)
      suite.addTest(mod.make_suite(basedistro=options.basedistro,
                                   arch=options.basearch))
    finally:
      fp and fp.close()

  result = None
  try:
    result = runner.run(suite)
  finally:
    if options.clear_test_cache:
      spintest.BUILD_ROOT.rm(recursive=True, force=True)

  if not result: # some sort of exception in the testing logic (can't currently happen)
    sys.exit(2)
  elif not result.wasSuccessful(): # not all tests succeeded
    sys.exit(1)
  else: # everything ok
    sys.exit(0)


def _testpath_normalize(path):
  path = pps.path(path)
  if not path.isabs() and path.splitall()[0] != 'modules':
    path = 'modules'/path # __rdiv__ is so cool
  path = path.abspath()
  if path.isdir():
    path = path/'__init__.py' # get the __init__.py inside the dir
  if path.endswith('.py'):
    path = path.replace('.py', '') # imp doesn't like .pys
  return path


if __name__ == '__main__': main()
