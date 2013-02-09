#!/usr/bin/python
#
# Copyright (c) 2012
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

import csv
import datetime
import subprocess
import sys
import time

from deploy.util import pps

from dtest import make_logger
from dtest.runtest import parse_cmd_args # use runtest's cmd parser

START = None # start time
TIMEFMT = '%Y-%m-%d %X'

opt_defaults = dict(
  distro   = 'centos',
  version  = '5',
  arch = 'i386',
  buildroot   = '/tmp/dtest',
  testlogfile = 'test.log',
  testloglevel = 2,
  libpath   = [],
  sharepath = [ pps.path(__file__).dirname.abspath() / '../share/deploy' ],
  clear_test_cache = True,
)

def reconstruct_cmd(options):
  # stupid method to reconstruct cmdline arguments from opts instance
  cmd = ['python', 'runtest.py']
  # always include these values because they're interesting to see in cmdline
  cmd += ['-d', options.distro]
  cmd += ['-f', options.version]
  cmd += ['-a', options.arch]
  # only include these values if they arent the defaults
  if options.buildroot != opt_defaults['buildroot']:
    cmd += ['-b', options.buildroot]
  if options.testlogfile != opt_defaults['testlogfile']:
    cmd += ['-l', options.testlogfile]
  if options.testloglevel != opt_defaults['testloglevel']:
    cmd += ['-v', str(options.testloglevel)]
  # the rest of these all imply their own defaults, so they don't need testing
  if not options.clear_test_cache:
    cmd += ['--no-clear-cache']
  if options.mainconfigpath:
    cmd += ['--distro-conf', options.mainconfigpath]
  for path in options.libpath:
    cmd += ['--lib-path', '%s' % path]
  for path in options.sharepath:
    cmd += ['--share-path', '%s' % path]

  return cmd

def _testpath_normalize(path):
  path = pps.path(path)
  if not path.isabs() and path.splitall()[0] != 'modules':
    path = 'modules'/path # __rdiv__ is so cool
  path = path.abspath()
  if path.isdir():
    path = path/'__init__.py' # get the __init__.py inside the dir
  path = path.splitext()[0] # get rid of .py, if present
  return path


def log_header(options):
  logfile = open(options.testlogfile, 'w+') # truncates file
  logger = make_logger(logfile, options.testloglevel)

  global START
  START = time.time()
  logger.log(0, '#' * 70)
  logger.log(0, '# Beginning test suite run for %s-%s-%s' \
                  % (options.distro, options.version, options.arch))
  logger.log(0, '# at %s' % time.strftime(TIMEFMT, time.localtime(START)))
  logger.log(0, '#' * 70)

  # make sure we close our handles on logfile
  del logger
  logfile.close()

def log_footer(options):
  logfile = open(options.testlogfile, 'a+') # don't truncate file
  logger = make_logger(logfile, options.testloglevel)

  end = time.time()
  logger.log(0, '=' * 70)
  logger.log(0, '= Test suite run for %s-%s-%s' \
                  % (options.distro, options.version, options.arch))
  logger.log(0, '= complete at %s (elapsed %s)' \
                  % (time.strftime(TIMEFMT, time.localtime(end)),
                     datetime.timedelta(seconds=int(round(end-START)))))
  logger.log(0, '=' * 70)

  # make sure we close our handles on logfile
  del logger
  logfile.close()

def log_summary(options, summaryfile):
  logfile = open(options.testlogfile, 'a+') # don't truncate file
  logger = make_logger(logfile, options.testloglevel)

  # formats, etc
  fmtstr   = '%-15s%8s%8s%8s%10s'
  efmtstr = '\033[1m%s\033[0;0m' % fmtstr
  tabwidth = 15+8+8+8+10 # sum of column widths, above
  width    = 70 # all other widths

  # modlist is a list of (ntests, nfailures, nerrors) tuples
  logger.log(0, '*' * width)
  logger.log(0, '* Test result summary:')
  logger.log(0, '*' * width)
  logger.log(0, fmtstr % ('module name', '# test', '# fail', '# err', 'time'))
  logger.log(0, '-' * tabwidth)

  ntests = nfails = nerrs = 0
  ttime = 0.0
  for mod in csv.reader(open(summaryfile)):
    ntests += int(mod[1])
    nfails += int(mod[2])
    nerrs  += int(mod[3])
    ttime  += float(mod[4])

    # choose fmtstr based on whether there were errors/failures or not
    fmt = fmtstr
    if int(mod[2]) > 0 or int(mod[3]) > 0:
      fmt = efmtstr

    logger.log(0, fmt % (mod[0], mod[1], mod[2], mod[3],
        datetime.timedelta(seconds=int(round(float(mod[4]))))))

  logger.log(0, '-' * tabwidth)
  logger.log(0, fmtstr % ('', ntests, nfails, nerrs,
                          datetime.timedelta(seconds=int(round(ttime)))))
  logger.log(0, '*' * width)

  # make sure we close our handles on logfile
  del logger
  logfile.close()

def main():
  import imp

  options, args = parse_cmd_args(opt_defaults)
  summaryfile = '%s.summary' % options.testlogfile
  pps.path(summaryfile).write_text('') # clear file

  if not args:
    args = [ x.basename.splitext()[0] for x in
               pps.path('modules').findpaths(mindepth=1, maxdepth=1)
               if x.basename != '__init__.py'
                  and x.basename != 'shared'
                  and x.ext != '.pyc'
                  and x.ext != 'pyo' ]

  cmd = reconstruct_cmd(options)

  log_header(options)
  r = 0
  for arg in args:
    # 0 = ok, 1 = test failure, 2 = test error, 3 = test engine error
    r = max(r, subprocess.call(cmd + [_testpath_normalize(arg)]))
  log_summary(options, summaryfile)
  log_footer(options)
  sys.exit(r)


if __name__ == '__main__': main()
