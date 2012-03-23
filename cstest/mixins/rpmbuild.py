#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
import yum

from rpmUtils import miscutils

from centosstudio.util import img
from centosstudio.util import pps

FLAGS_MAP = {
  0: '',
  rpm.RPMSENSE_EQUAL: '=',
  rpm.RPMSENSE_LESS: '<',
  rpm.RPMSENSE_GREATER: '>',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_LESS: '<=',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_GREATER: '>=',
}

#-------- TEST CASES --------#
class MkrpmRpmBuildMixinTestCase(object):
  @property
  def rpm_header(self):
    if self.event.rpm.rpm_path.exists():
      # we need an rpmdb with the pubkey imported to read the signed rpm header
      rpmdb_dir = self.event.mddir/'rpmdb'
      rpmdb_dir.rm(force=True)
      rpmdb_dir.mkdirs()
      rpm.addMacro('_dbpath', rpmdb_dir)
      ts = rpm.TransactionSet()
      ts.initDB()
      ts.pgpImportPubkey(yum.misc.procgpgkey(
                         self.event.cvars['gpg-signing-keys']
                                         ['pubkey'].read_text()))
      fdno = os.open(self.event.rpm.rpm_path, os.O_RDONLY)
      rpm_header = ts.hdrFromFdno(fdno)
      os.close(fdno)
      del ts
      rpm.delMacro('_dbpath')
      return rpm_header
    return None

  @property
  def img_path(self):
    if self.event.rpm.rpm_path.exists():
      if extracts.has_key(self.event.rpm.rpm_path):
        return extracts[self.event.rpm.rpm_path]
      working_dir = pps.path(tempfile.mkdtemp())
      img_path = pps.path(tempfile.mkdtemp())
      try:
        filename = working_dir / 'rpm.cpio'
        miscutils.rpm2cpio(os.open(self.event.rpm.rpm_path, os.O_RDONLY), filename.open('w+'))
        cpio = img.MakeImage(filename, 'cpio')
        cpio.open(point=img_path)
      finally:
        working_dir.rm(recursive=True, force=True)
      extracts[self.event.rpm.rpm_path] = img_path
      return img_path
    return None

  def check_inputs(self, what):
    if not self.event.io.list_output(what=what):
      raise RuntimeError("No '%s' specified. Probable error in test case." %
                         what)
    for file in self.event.io.list_output(what=what):
      self.failUnlessExists(file)
      self.failUnlessExists(self.img_path / file.relpathfrom(self.event.rpm.source_folder))

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
    for tag, rpmval, reqval in [('name', rpm.RPMTAG_NAME, 'name'),
                                ('desc', rpm.RPMTAG_DESCRIPTION, 'desc'),
                                ('summary', rpm.RPMTAG_SUMMARY, 'summary'),
                                ('license', rpm.RPMTAG_LICENSE, 'license'),
                                ('arch', rpm.RPMTAG_ARCH, 'arch'),
                                ('version', rpm.RPMTAG_VERSION, 'version'),
                                ('release', rpm.RPMTAG_RELEASE, 'release')]:
      expected = getattr(self.event.rpm, reqval)
      observed = self.rpm_header[rpmval]
      self.failUnless(observed == expected, "rpm %s incorrect: it is '%s', it should be '%s'" % \
                      (tag, observed, expected))

    observed_provides = self._get_provides()
    for dep in self.event.rpm.provides:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_provides,
                      "provision '%s' not actually provided" % dep)

    observed_requires = self._get_requires()
    for dep in self.event.rpm.requires:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_requires,
                      "requirement '%s' not actually required" % dep)

    observed_obsoletes = self._get_obsoletes()
    for dep in self.event.rpm.obsoletes:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_obsoletes,
                      "obsoleted '%s' not actually obsoleted" % dep)

class RpmCvarsTestCase(object):
  def check_cvars(self):
    for r in self.event.rpms:
      self.failUnless(r['rpm-name'] in self.event.cvars['rpmbuild-data'])
      if self.moduleid not in [ 'config-rpm', 'release-rpm' ] : continue
      self.failUnless(self.event.rpm.name == r['rpm-name'])
      self.failUnless(self.event.rpm.version == r['rpm-version'])
      self.failUnless(self.event.rpm.release == r['rpm-release'])
      self.failUnless(self.event.rpm.arch == r['rpm-arch'])
      self.failUnless(self.event.rpm.obsoletes == r['rpm-obsoletes'])

extracts = {}
