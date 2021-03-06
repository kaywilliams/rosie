#!/usr/bin/python
#
# Copyright (c) 2015
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

import optparse
import os
import sys
import unittest

from deploy.options import DeployOptionParser
from deploy.util import pps
from deploy.util.pps.cache import CacheHandler

from deploy.util.CleanHelpFormatter import CleanHelpFormatter

def get_opt_defaults():
  # get deploy default options
  opts,_ = DeployOptionParser().parse_args([])

  # override for use with dtest 
  opts.logthresh = 0
  opts.debug = True

  # return the result as a dict
  return vars(opts)

def parse_cmd_args(defaults=None):
  parser = optparse.OptionParser("usage: %prog [OPTIONS]",
                                 formatter=CleanHelpFormatter())

  parser.add_option('-o', '--os', metavar='OS',
    dest='os',
    default='centos',
    help='select the base operating system to test')
  parser.add_option('-f', '--version', metavar='VERSION',
    dest='version',
    default='5',
    help='select the version to test')
  parser.add_option('-a', '--arch', metavar='ARCH',
    dest='arch',
    default='i386',
    help='select the arch of the base operating system to test')

  parser.add_option('-b', '--build-root', metavar='DIRECTORY',
    dest='buildroot',
    default='/tmp/dtest',
    help='choose the location where builds should be performed')
  parser.add_option('--macro', metavar='ID:VALUE',
    dest='macros',
    default=[],
    action='append',
    help='id:value pair for replacing macros in definitions')
  parser.add_option('--deploy-conf', metavar='PATH',
    dest='mainconfigpath',
    help='specify path to a main config file')
  parser.add_option('--lib-path', metavar='PATH',
    dest='libpath',
    action='append',
    help='specify directory containing deploy library files')
  parser.add_option('--share-path', metavar='PATH',
    dest='sharepath',
    action='append',
    help='specify directory containing deploy share files')

  parser.add_option('-l', '--log-file', metavar='path',
    default='test.log',
    dest='testlogfile',
    help='specify the test log file to use')
  parser.add_option('-v', '--log-level', metavar='N',
    default=2,
    type='int',
    dest='testloglevel',
    help='specify the verbosity of the console log (0-2)')

  parser.add_option('--no-clear-cache',
    dest='clear_test_cache',
    default=True,
    action='store_false',
    help='don\'t clear event cache when done testing')

  parser.set_defaults(**(defaults or {}))

  return parser.parse_args(sys.argv[1:])

def main():
  import imp

  options, args = parse_cmd_args(get_opt_defaults())

  assert len(args) == 1
  modpath = pps.path(args[0])
  if modpath.basename == '__init__':
    modname = modpath.dirname.basename
  else:
    modname = modpath.basename

  sys.path = options.libpath + sys.path

  import dtest

  dtest.BUILD_ROOT = pps.path(options.buildroot)
  dtest.BUILD_ROOT.mkdirs()

  options.data_root = options.buildroot + '/data'
  pps.path(options.data_root).mkdirs()

  # use options as a convenient mechanism for passing additional attributes
  # to the TestBuild object
  options.cache_dir = dtest.BUILD_ROOT / '.cache'
  options.cache_handler = CacheHandler(options.cache_dir)

  dtest.EventTestCase.options = options

  runner = dtest.EventTestRunner(options.testlogfile, options.testloglevel)
  suite = unittest.TestSuite()

  cwd = os.getcwd() # save for later
  summaryfile = pps.path(cwd) / pps.path('%s.summary' % options.testlogfile)

  fp = None
  try:
    fp,p,d = imp.find_module(modpath.basename, [modpath.dirname])
    mod = imp.load_module('test-%s' % modname, fp, p, d)
    suite.addTest(mod.make_suite(os=options.os,
                                 version=options.version,
                                 arch=options.arch,
                                 ))
  except:
    summaryfile.write_lines(['%s,%s,%s,%s,%s,%s'
      % (modname, "0", "0", "0", "0", "Module load failed")],
      append=True)
    raise
  finally:
    fp and fp.close()

  result = None
  try:
    result = runner.run(suite)
  finally:
    if options.clear_test_cache:
      dtest.BUILD_ROOT.rm(recursive=True, force=True)

  os.chdir(cwd) # make sure we're back where we started

  # write results to summaryfile
  summaryfile.write_lines(['%s,%s,%s,%s,%s,%s'
    % (modname,
       result.testsRun,
       len(result.failures),
       len(result.errors),
       result.duration,
       "")],
    append=True)

  if not result: # some sort of exception in the testing logic (can't currently happen)
    sys.exit(3)
  elif len(result.errors) > 0:
    sys.exit(2)
  elif len(result.failures) > 0:
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
