#
# Copyright (c) 2013
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
import os
import rpm
import tempfile
import yum

from rpmUtils import miscutils

from deploy.util import img
from deploy.util import pps
from deploy.util import shlib 

FLAGS_MAP = {
  0: '',
  rpm.RPMSENSE_EQUAL: '=',
  rpm.RPMSENSE_LESS: '<',
  rpm.RPMSENSE_GREATER: '>',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_LESS: '<=',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_GREATER: '>=',
}

PUBKEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

mQGiBE7iLHkRBACbHdCzgO5Jac4LRbQwKoX+1ltYHrvvc/WsnhuPN5HXhvkPTA+/
rbsCxm8oqzP5puu7rimcnZkHN7pN/8uKj5Vd7EbaVNSWUg7rfhDlxg/KxDAnXPuI
JBhER92JfU0y5D1SOb4SmSJ32E79zrDVFt0XFlOP6biwFS/RGHRJxzjGlwCgnOcN
AYveV6pXd8Ec9OX6Lea+46sD/289sU6VeSg9KruXM67LjDei/P8aDAGsABdhq57F
L7eOcWewZ0UZDQh1zSB+r0DoWF6rpj7oQ/yRWoHWXgFfUX8tL5AV7HuNmsxAfvy/
/xBs8YVgBxieeiWrBGxcBQRdXZDSSOz2WYExir5y4/ehn3Upn5WKeUqkP5uAsQkB
XFOyA/wOOd4azDKd0uouLgluJbqYMSlRDoigNbHWVPAM3PvZdusgzP2JO91IxCHD
JeCpZWgfN29g8py66PkXg7EfsisQqVO3/42me96Tqb/77Y8kSbubWQ4uVQd5YB8z
0sGT71S6NrAnhqyqs7toMjUGO5JuMfnP/hgITk967nV5jZowX7QQdGVzdCBzaWdu
aW5nIGtleYhgBBMRAgAgBQJO4ix5AhsjBgsJCAcDAgQVAggDBBYCAwECHgECF4AA
CgkQyubdJwqXVrONfQCfUS5Qb14tm2ADjxLoZRuYtEpn9WsAoJwnvOfR7XE/Qjqq
s6JooAwdguR6uQENBE7iLHoQBACvveBthapADqBic6ijcQbt1Hb6E/9HAwxubRpj
yl0g8uC1ZxfcQKJ1GT983Bx/okvP73olKOxV1xnlpT7DV+6EYucIGVyW55mrxI3H
P7o1Ox1wvh7fP/pm6Yf//OLF9lFUh3h0/mYziqAaf0L/Vm3aWu9Hl02IJToVifAC
GemE7wADBQQAovTMQ5k8RG1k5jCUqRV280FKInE24M/75YbNXwdTkGfp9pl1ceNJ
1vhlZg3JuHnZ0uw0p3la7WUCut0afy7vCRQPD4g8E57vfBFzOpiifXbEP5VHa37e
hY3hoknv0N3UP7EjWxUoifSi1VsV8WMHcJVxKgu6//oXsHQ6GSypR1aISQQYEQIA
CQUCTuIsegIbDAAKCRDK5t0nCpdWs0DuAKCXthQjeX5H4DL9sZUkxk+k4wiHtgCf
TBefZqqYtL+kacCEgCIYH2Fhm0I=
=9xNj
-----END PGP PUBLIC KEY BLOCK-----"""

SECKEY = """-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1.4.5 (GNU/Linux)

lQG7BE7iLHkRBACbHdCzgO5Jac4LRbQwKoX+1ltYHrvvc/WsnhuPN5HXhvkPTA+/
rbsCxm8oqzP5puu7rimcnZkHN7pN/8uKj5Vd7EbaVNSWUg7rfhDlxg/KxDAnXPuI
JBhER92JfU0y5D1SOb4SmSJ32E79zrDVFt0XFlOP6biwFS/RGHRJxzjGlwCgnOcN
AYveV6pXd8Ec9OX6Lea+46sD/289sU6VeSg9KruXM67LjDei/P8aDAGsABdhq57F
L7eOcWewZ0UZDQh1zSB+r0DoWF6rpj7oQ/yRWoHWXgFfUX8tL5AV7HuNmsxAfvy/
/xBs8YVgBxieeiWrBGxcBQRdXZDSSOz2WYExir5y4/ehn3Upn5WKeUqkP5uAsQkB
XFOyA/wOOd4azDKd0uouLgluJbqYMSlRDoigNbHWVPAM3PvZdusgzP2JO91IxCHD
JeCpZWgfN29g8py66PkXg7EfsisQqVO3/42me96Tqb/77Y8kSbubWQ4uVQd5YB8z
0sGT71S6NrAnhqyqs7toMjUGO5JuMfnP/hgITk967nV5jZowXwAAnA12xL8lKygY
avXfoZC4hAHepi0VCaS0EHRlc3Qgc2lnbmluZyBrZXmIYAQTEQIAIAUCTuIseQIb
IwYLCQgHAwIEFQIIAwQWAgMBAh4BAheAAAoJEMrm3ScKl1azjX0An1EuUG9eLZtg
A48S6GUbmLRKZ/VrAKCcJ7zn0e1xP0I6qrOiaKAMHYLkep0BMgRO4ix6EAQAr73g
bYWqQA6gYnOoo3EG7dR2+hP/RwMMbm0aY8pdIPLgtWcX3ECidRk/fNwcf6JLz+96
JSjsVdcZ5aU+w1fuhGLnCBlclueZq8SNxz+6NTsdcL4e3z/6ZumH//zixfZRVId4
dP5mM4qgGn9C/1Zt2lrvR5dNiCU6FYnwAhnphO8AAwUEAKL0zEOZPERtZOYwlKkV
dvNBSiJxNuDP++WGzV8HU5Bn6faZdXHjSdb4ZWYNybh52dLsNKd5Wu1lArrdGn8u
7wkUDw+IPBOe73wRczqYon12xD+VR2t+3oWN4aJJ79Dd1D+xI1sVKIn0otVbFfFj
B3CVcSoLuv/6F7B0OhksqUdWAAD5AfL1s+wz653stZOKhxMX1S9gbq4A9nQesx45
o2iyjegR7ohJBBgRAgAJBQJO4ix6AhsMAAoJEMrm3ScKl1azQO4An3vR7ZjQ80tD
MkKc5Q91TmwC5A7jAJ9jvRPHOVwYC+sHFL4mOt/9XVaFdg==
=k9wN
-----END PGP PRIVATE KEY BLOCK-----"""

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
        shlib.execute('/usr/bin/rpmdev-extract -C %s %s | grep -v "\.spec"'
                      % (img_path, self.event.rpm.rpm_path))
        #miscutils.rpm2cpio(os.open(self.event.rpm.rpm_path, os.O_RDONLY), filename.open('w+'))
        #cpio = img.MakeImage(filename, 'cpio')
        #cpio.open(point=img_path)
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
      self.failUnlessExists(self.img_path / '%s-%s-%s.%s' %
                            (self.event.rpm.name, self.event.rpm.version,
                             self.event.rpm.release, self.event.rpm.arch)
                             / file.relpathfrom(self.event.rpm.source_folder))

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
