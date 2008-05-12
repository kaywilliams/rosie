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
import os
import rpm
import tempfile

from rpmUtils import miscutils

from rendition import img
from rendition import pps

FLAGS_MAP = {
  0: '',
  rpm.RPMSENSE_EQUAL: '=',
  rpm.RPMSENSE_LESS: '<',
  rpm.RPMSENSE_GREATER: '>',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_LESS: '<=',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_GREATER: '>=',
}

#-------- SUPER (ABSTRACT) CLASSES ----------#
class ExtractMixin(object):
  def _get_imgpath(self):
    if self.event.rpm_path.exists():
      if extracts.has_key(self.event.rpm_path):
        return extracts[self.event.rpm_path]
      working_dir = pps.path(tempfile.mkdtemp())
      img_path = pps.path(tempfile.mkdtemp())
      try:
        filename = working_dir / 'rpm.cpio'
        miscutils.rpm2cpio(os.open(self.event.rpm_path, os.O_RDONLY), filename.open('w+'))
        cpio = img.MakeImage(filename, 'cpio')
        cpio.open(point=img_path)
      finally:
        working_dir.rm(recursive=True, force=True)
      extracts[self.event.rpm_path] = img_path
      return img_path
    return None
  img_path = property(_get_imgpath)

#-------- TEST CASES --------#
class InputFilesMixinTestCase(ExtractMixin):
  def check_inputs(self):
    for id in self.event.ids:
      for file in self.event.io.list_output(what=id):
        self.failUnlessExists(file)
        self.failUnlessExists(self.img_path / file.relpathfrom(self.event.build_folder))

class RpmBuildMixinTestCase(object):
  def _get_rpmheader(self):
    if self.event.rpm_path.exists():
      if headers.has_key(self.event.rpm_path):
        return headers[self.event.rpm_path]
      ts = rpm.TransactionSet()
      fdno = os.open(self.event.rpm_path, os.O_RDONLY)
      rpm_header = ts.hdrFromFdno(fdno)
      os.close(fdno)
      headers[self.event.rpm_path] = rpm_header
      del ts
      return rpm_header
    return None
  rpm_header = property(_get_rpmheader)

  def _get_provides(self):
    return self._get_deps(rpm.RPMTAG_PROVIDENAME,
                          rpm.RPMTAG_PROVIDEFLAGS,
                          rpm.RPMTAG_PROVIDEVERSION)

  def _get_obsoletes(self):
    return self._get_deps(rpm.RPMTAG_OBSOLETENAME,
                          rpm.RPMTAG_OBSOLETEFLAGS,
                          rpm.RPMTAG_OBSOLETEVERSION)

  def _get_requires(self):
    return self._get_deps(rpm.RPMTAG_REQUIRENAME,
                          rpm.RPMTAG_REQUIREFLAGS,
                          rpm.RPMTAG_REQUIREVERSION)

  def _get_deps(self, namestag, flagstag, versionstag):
    names = self.rpm_header[namestag]
    flags = self.rpm_header[flagstag]
    versions = self.rpm_header[versionstag]
    self.failUnless(len(names) == len(flags) == len(versions))
    deps = []
    for i in xrange(len(names)):
      name = names[i]
      flag = flags[i]
      version = versions[i]
      if name.startswith('config(') or name.startswith('rpmlib(') or \
         name.startswith('/'):
        continue
      try:
        dep = '%s %s %s' % (name, FLAGS_MAP[flag], version)
      except KeyError:
        raise KeyError("Unknown sense '%d' used for package '%s' (version=%s)"
                       % (flag, name, version))
      deps.append(dep.strip())
    return deps

  def check_header(self):
    for tag, rpmval, reqval in [('name', rpm.RPMTAG_NAME, 'rpm_name'),
                                ('arch', rpm.RPMTAG_ARCH, 'rpm_arch'),
                                ('version', rpm.RPMTAG_VERSION, 'rpm_version'),
                                ('release', rpm.RPMTAG_RELEASE, 'rpm_release')]:
      expected = getattr(self.event, reqval)
      observed = self.rpm_header[rpmval]
      self.failUnless(observed == expected, "rpm %s incorrect: it is '%s', it should be '%s'" % \
                      (tag, observed, expected))

    observed_provides = self._get_provides()
    for dep in self.event.rpm_provides:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_provides,
                      "provision '%s' not actually provided" % dep)

    observed_requires = self._get_requires()
    for dep in self.event.rpm_requires:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_requires,
                      "requirement '%s' not actually required" % dep)

    observed_obsoletes = self._get_obsoletes()
    for dep in self.event.rpm_obsoletes:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_obsoletes,
                      "obsoleted '%s' not actually obsoleted" % dep)

class RpmCvarsTestCase(object):
  def check_cvars(self):
    cvars = self.event.cvars['custom-rpms-data'][self.event.id]
    self.failUnless(self.event.packagereq_default == cvars['packagereq-default'])
    self.failUnless(self.event.packagereq_requires == cvars['packagereq-requires'])
    self.failUnless(self.event.packagereq_type == cvars['packagereq-type'])
    self.failUnless(self.event.rpm_name == cvars['rpm-name'])
    self.failUnless(self.event.rpm_obsoletes == cvars['rpm-obsoletes'])
    self.failUnless(self.event.rpm_provides == cvars['rpm-provides'])
    self.failUnless(self.event.rpm_requires == cvars['rpm-requires'])
    self.failUnless(self.event.rpm_path == cvars['rpm-path'])
    self.failUnless(self.event.srpm_path == cvars['srpm-path'])

headers = {}
extracts = {}
