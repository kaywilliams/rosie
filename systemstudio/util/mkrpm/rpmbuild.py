#
# Copyright (c) 2011
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
"""
Module that can be used to build RPMs.
"""

__author__ = 'Uday Prakash <uprakash@renditionsoftware.com>'
__date__   = 'April 19, 2007'

import os
import tempfile
import sys

from systemstudio.util import pps
from systemstudio.util import shlib
from systemstudio.util import sync

from systemstudio.util.mkrpm.setup import SETUP_PY_TEXT

__all__ = [
  'RpmBuilderException',
  'RpmBuilder',
  'build',
]

def build(source_path, output_path, bdist_base=None, rpm_base=None,
          dist_dir=None, quiet=True, createrepo=True,
          keep_source=True, *args, **kwargs):
  """
  Function that builds RPMs. The path is the path to the files and
  the directories that are installed by the RPM. The setup.py,
  setup.cfg, MANIFEST[.in] etc. should exist at path/.The output
  parameter is the path to the output folder. The RPM build process
  creates an RPMS/ and SRPMS/ folder inside the output/ folder if it
  doesn't exist, and copies the binary RPM to the RPMS/ folder and
  the source RPM to the SRPMS/ folder. Createrepo is run on the
  RPMS/ folder, unless the createrepo parameter is unset. The
  changelog parameter it RPM's .spec file's change log which has to
  be specified. If changelog is None, the .spec file in the RPM
  created will have no changelog section.
  """
  builder = RpmBuilder(source_path=source_path,
             output_path=output_path,
             bdist_base=bdist_base,
             rpm_base=rpm_base,
             dist_dir=dist_dir,
             keep_temp=keep_source,
             createrepo=createrepo,
             quiet=quiet, *args, **kwargs)
  builder.build()
  builder.output()

class RpmBuilderException(Exception):
  """
  Exception raised during the RPM build process.
  """

class RpmBuilder:
  """
  Class used to build RPMs.
  """

  def __init__(self, source_path, output_path,
         bdist_base='/usr/src/redhat',
         rpm_base='/usr/src/redhat',
         dist_dir=None, keep_temp=False,
         createrepo=True, quiet=False, *args, **kwargs):
    self.source_path = pps.path(source_path)
    self.output_path = pps.path(output_path)
    self.bdist_base  = pps.path(bdist_base)
    self.rpm_base  = pps.path(rpm_base)
    if dist_dir:
      self.dist_dir = pps.path(dist_dir)
    else:
      self.dist_dir = self.bdist_base / 'dist'
    self.keep_temp = keep_temp
    self.createrepo = createrepo
    self.quiet = quiet
    self.extra_flags = args
    self.extra_args = kwargs

  def prebuild(self):
    pass

  def build(self):
    self.prebuild()

    self.bdist_base.mkdirs()
    self.rpm_base.mkdirs()
    self.dist_dir.mkdirs()

    setuppy = self.source_path / 'setup.py'
    if not setuppy.exists():
      f = setuppy.open('w')
      f.write(SETUP_PY_TEXT)
      f.close()
    self._build()
    self.postbuild()

  def _build(self):
    if self.quiet:
      orig_in = os.dup(0)
      orig_out = os.dup(1)
      orig_err = os.dup(2)
      for (fileno, mode) in [(0, os.O_RDONLY),
                             (1, os.O_WRONLY)]:
        fdno = os.open('/dev/null', mode)
        if fdno != fileno:
          os.dup2(fdno, fileno)
          os.close(fdno)

      # have to special case stderr so that when an exception
      # is raised, we have something to print out
      tfdno,tfile = tempfile.mkstemp()
      errin = os.open(tfile, os.O_RDWR|os.O_CREAT)
      os.dup2(errin, 2)

    pid = os.fork()

    # child process
    if not pid:
      argv = ['python', 'setup.py', 'bdist_rpm']
      if self.bdist_base:
        argv.extend(['--bdist-base', str(self.bdist_base)])
      if self.rpm_base:
        argv.extend(['--rpm-base', str(self.rpm_base)])
      if self.dist_dir:
        argv.extend(['--dist-dir', str(self.dist_dir)])
      for extra_flag in self.extra_flags:
        argv.append('--%s' % extra_flag.replace('_', '-'))
      for arg, value in self.extra_args:
        argv.extend(['--%s' % arg.replace('_', '-'), str(value)])
      if self.quiet:
        argv.append('--quiet')
      os.chdir(self.source_path)
      os.execv(sys.executable, argv)

    # parent process
    failed = False
    try:
      pid2, status = os.waitpid(pid, 0)
      assert pid2 == pid
      if not os.WIFEXITED(status) or os.WEXITSTATUS(status):
        failed = True
        if self.quiet:
          os.dup2(orig_in, 0)
          os.dup2(orig_out, 1)
          os.dup2(orig_err, 2)
          elog = os.fdopen(errin, 'r')
          elog.seek(0)
          msg = elog.read()
          elog.close()
          os.close(orig_in)
          os.close(orig_out)
          os.close(orig_err)
          raise RpmBuilderException("rpm build failed:\n%s" % msg)
        else:
          raise RpmBuilderException("rpm build failed")
    finally:
      if self.quiet:
        os.close(tfdno)
        pps.path(tfile).rm(force=True)
        if not failed:
          os.dup2(orig_in, 0)
          os.dup2(orig_out, 1)
          os.dup2(orig_err, 2)
          os.close(orig_in)
          os.close(orig_out)
          os.close(orig_err)
          os.close(errin)

    self.postbuild()

  def postbuild(self):
    pass

  def preoutput(self):
    pass

  def output(self):
    """
    Copy the {S}RPMs to the output folder and run createrepo.
    """
    self.preoutput()

    sources = self.dist_dir

    rpms_dir = self.output_path / 'RPMS'
    srpms_dir = self.output_path / 'SRPMS'

    rpms_dir.mkdirs()
    srpms_dir.mkdirs()
    for rpm in sources.findpaths(glob='*.[Rr][Pp][Mm]',
                                 nglob='*[Ss][Rr][Cc].[Rr][Pp][Mm]'):
      sync.sync(rpm, rpms_dir)
    for srpm in sources.findpaths(glob='*[Ss][Rr][Cc].[Rr][Pp][Mm]'):
      sync.sync(srpm, srpms_dir)

    if self.createrepo:
      shlib.execute('createrepo %s' % rpms_dir)
    if not self.keep_temp:
      self.source_path.rm(recursive=True, force=True)
    sources.rm(recursive=True, force=True)

    self.postoutput()

  def postoutput(self):
    pass
