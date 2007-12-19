from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE, SRPM_REGEX
from dimsbuild.event     import Event

from dimsbuild.modules.shared import ExtractMixin, RpmNotFoundError

P = pps.Path

API_VERSION = 5.0
EVENTS = {'installer': ['ReleaseFilesEvent']}

DEFAULT_SET = ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README*',
               '*-RPM-GPG', 'RPM-GPG-KEY*', 'RELEASE-NOTES*']

class ReleaseFilesEvent(Event, ExtractMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'release-files',
      requires = ['rpms-directory'],
      conditionally_comes_after = ['gpgsign'],
    )

    self.DATA = {
      'variables': ['product'],
      'config':    ['.'],
      'input' :    [],
      'output':    [],
    }

  def setup(self):
    self.DATA['input'].extend(self._find_rpms())
    self.diff.setup(self.DATA)
    self.io.setup_sync(self.SOFTWARE_STORE, xpaths=['path'], id='release-files-input')

  def run(self):
    self.cvars.setdefault('release-files', [])
    self._extract()

  def apply(self):
    existing = []
    for item in DEFAULT_SET:
      existing.extend(self.SOFTWARE_STORE.listdir(glob=item))
    if existing:
      self.cvars.setdefault('release-files', []).extend(existing)
    self.io.clean_eventcache()

  def _generate(self, working_dir):
    self.io.sync_input(link=True, cache=False, what='release-files-input')
    rtn = []
    if self.config.get('@use-default-set', 'True') in BOOLEANS_TRUE:
      for item in DEFAULT_SET:
        for file in working_dir.findpaths(glob=item):
          self.link(file, self.SOFTWARE_STORE)
          rtn.append(self.SOFTWARE_STORE / file.basename)
    self.cvars['release-files'].extend(rtn)
    return rtn

  def _find_rpms(self):
    rpmnames = self.config.xpath('package/text()',
                                 [ '%s-release' % self.product ])
    rpmset = set()
    for rpmname in rpmnames:
      for rpm in self.cvars['rpms-directory'].findpaths(
          glob='%s-*-*' % rpmname, nregex=SRPM_REGEX):
        rpmset.add(rpm)

    if not rpmset:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        for rpm in self.cvars['rpms-directory'].findpaths(
            glob=glob, nregex=SRPM_REGEX):
          rpmset.add(rpm)
        if not rpmset:
          raise RpmNotFoundError("missing release RPM(s)")
    return rpmset

  def verify_cvars(self):
    "verify all cvars exist"
    self.verifier.failUnless(self.cvars['release-files'] is not None,
      "'release-files' event generated no content")
