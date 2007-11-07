from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE, SRPM_REGEX
from dimsbuild.event     import Event

from dimsbuild.modules.shared import ExtractMixin, RpmNotFoundError

P = pps.Path

API_VERSION = 5.0
EVENTS = {'installer': ['ReleaseFilesEvent']}

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
    
  def run(self):
    self._extract()

  def apply(self):
    self.io.clean_eventcache()

  def _generate(self, working_dir):
    files = {}
    rtn = []
    for path in self.config.xpath('path', []):
      source = P(path.text)
      dest = self.SOFTWARE_STORE/path.attrib['dest']
      files[source] = dest
    if self.config.get('include-in-tree/@use-default-set', 'True') \
           in BOOLEANS_TRUE:
      for default_item in ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README',
                           '*-RPM-GPG', 'RPM-GPG-KEY-*', 'RPM-GPG-KEY-beta',
                           'README-BURNING-ISOS-en_US.txt', 'RELEASE-NOTES-en_US.html']:
        for item in working_dir.findpaths(glob=default_item):
          files[item] = self.SOFTWARE_STORE
    
    for source in files.keys():
      dest = files[source]
      if source.isfile() and dest.isdir():
        rtn.append(dest/source.basename)
      self.link(source, dest)
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
