import os
import rpm
import tempfile

from rpmUtils import miscutils

from dims import img
from dims import pps

from test import EventTest

P = pps.Path

#-------- SUPER (ABSTRACT) CLASSES ----------#
class RpmEventTest(EventTest):
  def __init__(self, eventid, conf):
    EventTest.__init__(self, eventid, conf)

  def _get_rpmpath(self):
    return self.event.METADATA_DIR / \
           "%s/RPMS/%s-%s-%s.%s.rpm" % (self.eventid, self.event.rpmname,
                                        self.event.version, self.event.release,
                                        self.event.arch)
    return None
  rpm_path = property(_get_rpmpath)

  def _get_srpmpath(self):
    return self.event.METADATA_DIR / \
           "%s/SRPMS/%s-%s-%s.src.rpm" % (self.eventid, self.event.rpmname,
                                          self.event.version, self.event.release)
  srpm_path = property(_get_srpmpath)

  def setUp(self):
    EventTest.setUp(self)

class ExtractMixin(object):
  def __init__(self):
    pass

  def _get_imgpath(self):
    if self.event._run:
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
class InputFilesMixinTestCase(RpmEventTest, ExtractMixin):
  def __init__(self, eventid, conf):
    RpmEventTest.__init__(self, eventid, conf)
    ExtractMixin.__init__(self)

  def check_inputs(self):
    for k,v in self.event.installinfo.items():
      xpath, dst, defmode = v
      if xpath and self.event.config.xpath(xpath, None):
        for file in self.event.io.list_output(id=xpath):
          self.failUnless(file.exists(), "missing %s" % file)
          self.failUnless(self.img_path / file.lstrip('/'))

class LocalFilesMixinTestCase(RpmEventTest, ExtractMixin):
  def __init__(self, eventid, conf):
    RpmEventTest.__init__(self, eventid, conf)
    ExtractMixin.__init__(self)

  def check_locals(self):
    for id in self.event.fileslocals.keys():
      file = self.event.build_folder / id
      self.failUnless(file.exists(), "missing %s" % file)
      for l in [ P(x) for x in self.event.fileslocals[id]['locations']]:
        self.failUnless((self.img_path / l.lstrip('/')).exists())

class RpmBuildMixinTestCase(RpmEventTest):
  def __init__(self, eventid, conf):
    RpmEventTest.__init__(self, eventid, conf)

  def _get_rpmheader(self):
    if self.event._run:
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

  def check_header(self):
    for tag, rpmval, reqval in [('name', rpm.RPMTAG_NAME, 'rpmname'),
                                ('arch', rpm.RPMTAG_ARCH, 'arch'),
                                ('version', rpm.RPMTAG_VERSION, 'version'),
                                ('release', rpm.RPMTAG_RELEASE, 'release')]:
      expected = getattr(self.event, reqval)
      observed = self.rpm_header[rpmval]
      self.failUnless(observed == expected, "rpm %s incorrect: it is '%s', it should be '%s'" % \
                      (tag, observed, expected))
    ## FIXME: do some magickery for obsoletes, provides and requires

class RpmCvarsTestCase(RpmEventTest):
  def __init__(self, eventid, conf):
    RpmEventTest.__init__(self, eventid, conf)

  def check_cvars(self):
    self.failUnless(self.rpm_path in self.event.cvars['custom-rpms'])
    self.failUnless(self.srpm_path in self.event.cvars['custom-srpms'])

headers = {}
extracts = {}
