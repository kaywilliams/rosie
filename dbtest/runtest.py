import optparse
import sys
import unittest

from dims import pps

from dims.CleanHelpFormatter import CleanHelpFormatter

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
  return EventTestLogContainer([console, logfile])

def parse_cmd_args():
  parser = optparse.OptionParser("usage: %prog [OPTIONS]",
                                 formatter=CleanHelpFormatter())

  parser.add_option('-d', '--base-distro', metavar='DISTRO',
    dest='basedistro',
    default='fedora-6',
    help='select the distribution to test')
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

  sys.path = options.libpath + sys.path

  from dbtest import EventTestLogContainer, EventTestRunner, EventTestCase

  EventTestCase.options = options

  runner = EventTestRunner()
  suite = unittest.TestSuite()

  if not args:
    args = [ pps.Path(__file__).abspath().dirname/'__init__.py' ]
  for arg in args:
    testpath = _testpath_normalize(arg)
    fp = None
    try:
      fp,p,d = imp.find_module(testpath.basename, [testpath.dirname])
      mod = imp.load_module('test-%s' % testpath.dirname.basename, fp, p, d)
      suite.addTest(mod.make_suite(basedistro=options.basedistro))
    finally:
      fp and fp.close()

  runner.run(suite)

def _testpath_normalize(path):
  path = pps.Path(path)
  if not path.isabs() and path.tokens[0] != 'modules':
    path = 'modules'/path # __rdiv__ is so cool
  path = path.abspath()
  if path.isdir():
    path = path/'__init__.py' # get the __init__.py inside the dir
  if path.endswith('.py'):
    path = path.replace('.py', '') # imp doesn't like .pys
  return path


if __name__ == '__main__': main()
