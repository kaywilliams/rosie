import optparse
import sys
import unittest

from dims import pps

from dims.CleanHelpFormatter import CleanHelpFormatter

from dbtest import EventTestLogContainer, EventTestRunner, EventTestCase

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
)
test_options = None # set on running parse_cmd_args(), below


LOGFILE = open('test.log', 'w+')

def make_logger(threshold):
  console = logger.Logger(threshold=threshold, file_object=sys.stdout)
  logfile = logger.Logger(threshold=threshold, file_object=LOGFILE)
  return EventTestLogContainer([console, logfile])

def parse_cmd_args():
  parser = optparse.OptionParser("usage: %prog [OPTIONS]",
                                 formatter=CleanHelpFormatter())

  parser.add_option('--skip', metavar='MODULEID',
    dest='skip_test',
    action='append',
    help='skip testing of a certain event, by id')
  parser.add_option('--dimsbuild-conf', metavar='PATH',
    dest='mainconfigpath',
    help='specify path to a main config file')
  parser.add_option('--lib-path', metavar='PATH',
    dest='libpath',
    action='append',
    help='specify directory containing dimsbuild library files')
  parser.add_option('--share-path', metavar='PATH',
    dest='sharepath',
    action='append',
    help='specify directory containing dimsbuild share files')

  parser.set_defaults(**opt_defaults)

  return parser.parse_args(sys.argv[1:])

def main():
  import imp

  options, args = parse_cmd_args()
  EventTestCase.options = options

  runner = EventTestRunner()
  suite = unittest.TestSuite()

  fp = None
  try:
    testpath = pps.Path(args[0].replace('.py', '')).abspath()
    fp,p,d = imp.find_module(testpath.basename, [testpath.dirname])
    mod = imp.load_module('test-%s' % testpath.dirname.basename, fp, p, d)
  finally:
    fp and fp.close()

  suite.addTest(mod.make_suite())

  runner.run(suite)


if __name__ == '__main__': main()
