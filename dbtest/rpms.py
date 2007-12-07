import os
import rpm
import tempfile

from rpmUtils import miscutils

from dims import img
from dims import pps

from dbtest import EventTestCase

P = pps.Path

FLAGS_MAP = {
  0: '',
  rpm.RPMSENSE_EQUAL: '=',
  rpm.RPMSENSE_LESS: '<',
  rpm.RPMSENSE_GREATER: '>',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_LESS: '<=',
  rpm.RPMSENSE_EQUAL | rpm.RPMSENSE_GREATER: '>=',
}


#-------- SUPER (ABSTRACT) CLASSES ----------#
class RpmEventTestCase(EventTestCase):
  def _get_rpmpath(self):
    return self.event.METADATA_DIR / \
           "%s/RPMS/%s-%s-%s.%s.rpm" % (self.eventid, self.event.rpm_name,
                                        self.event.version, self.event.release,
                                        self.event.arch)
    return None
  rpm_path = property(_get_rpmpath)

  def _get_srpmpath(self):
    return self.event.METADATA_DIR / \
           "%s/SRPMS/%s-%s-%s.src.rpm" % (self.eventid, self.event.rpm_name,
                                          self.event.version, self.event.release)
  srpm_path = property(_get_srpmpath)

  def setUp(self):
    EventTestCase.setUp(self)

class ExtractMixin(object):
  def _get_imgpath(self):
    if self.rpm_path.exists():
      if extracts.has_key(self.rpm_path):
        return extracts[self.rpm_path]
      working_dir = P(tempfile.mkdtemp())
      img_path = P(tempfile.mkdtemp())
      try:
        filename = working_dir / 'rpm.cpio'
        miscutils.rpm2cpio(os.open(self.rpm_path, os.O_RDONLY), filename.open('w+'))
        cpio = img.MakeImage(filename, 'cpio')
        cpio.open(point=img_path)
      finally:
        working_dir.rm(recursive=True, force=True)
      extracts[self.rpm_path] = img_path
      return img_path
    return None
  img_path = property(_get_imgpath)

#-------- TEST CASES --------#
class InputFilesMixinTestCase(RpmEventTestCase, ExtractMixin):
  def check_inputs(self):
    for k,v in self.event.installinfo.items():
      xpath, dst, defmode = v
      if xpath and self.event.config.xpath(xpath, None):
        for file in self.event.io.list_output(id=xpath):
          self.failUnless(file.exists(), "missing %s" % file)
          self.failUnless(self.img_path / file.lstrip('/'))

class LocalFilesMixinTestCase(RpmEventTestCase, ExtractMixin):
  def check_locals(self):
    for id in self.event.fileslocals.keys():
      file = self.event.build_folder / id
      self.failUnless(file.exists(), "missing %s" % file)
      for l in [ P(x) for x in self.event.fileslocals[id]['locations']]:
        self.failUnless((self.img_path / l.lstrip('/')).exists())

class RpmBuildMixinTestCase(RpmEventTestCase):
  def _get_rpmheader(self):
    if self.rpm_path.exists():
      if headers.has_key(self.rpm_path):
        return headers[self.rpm_path]
      ts = rpm.TransactionSet()
      fdno = os.open(self.rpm_path, os.O_RDONLY)
      rpm_header = ts.hdrFromFdno(fdno)
      os.close(fdno)
      headers[self.rpm_path] = rpm_header
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
    for dep in self.event.provides:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_provides,
                      "provision '%s' not actually provided" % dep)

    observed_requires = self._get_requires()
    for dep in self.event.requires:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_requires,
                      "requirement '%s' not actually required" % dep)

    observed_obsoletes = self._get_obsoletes()
    for dep in self.event.obsoletes:
      dep = dep.replace('==', '=') # for consistency
      self.failUnless(dep in observed_obsoletes,
                      "obsoleted '%s' not actually obsoleted" % dep)

class RpmCvarsTestCase(RpmEventTestCase):
  def check_cvars(self):
    self.failUnless(self.rpm_path in self.event.cvars['custom-rpms'])
    self.failUnless(self.srpm_path in self.event.cvars['custom-srpms'])

headers = {}
extracts = {}
