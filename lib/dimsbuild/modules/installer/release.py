from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE, SRPM_REGEX
from dimsbuild.event     import Event

from dimsbuild.modules.installer.lib import ExtractMixin, RpmNotFoundError

P = pps.Path

API_VERSION = 5.0


class ReleaseFilesEvent(Event, ExtractMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'release-files',
      requires = ['rpms-directory'],
      conditionally_requires = ['gpgsign'],
    )
    
    self.DATA = {
      'config': ['/distro/installer/release-files'],
      'input' : [],
      'output': [],
    }
    
  def validate(self):
    self._validate('/distro/installer/release-files', 'release-files.rng')
  
  def setup(self):
    self.DATA['input'].extend(self._find_rpms())
    self.setup_diff(self.DATA)
    
  def run(self):
    self.log(0, "synchronizing release files")
    self._extract()

  def _generate(self, working_dir):
    files = {}
    rtn = []    
    for path in self.config.xpath('/distro/installer/release-files/path', []):
      source = P(path.text)
      dest = self.SOFTWARE_STORE/path.attrib['dest']
      files[source] = dest
    if self.config.get('/distro/installer/release-files/include-in-tree/@use-default-set', 'True') \
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
      self.copy(source, dest, link=True)
    return rtn
  
  def _find_rpms(self):
    rpmnames = self.config.xpath('/distro/installer/release-files/package/text()',
                                ['%s-release' %(self.product,)])
    rpmset = set()
    for rpmname in rpmnames:
      for rpm in self.cvars['rpms-directory'].findpaths(
          glob='%s-*-*' % rpmname, nregex=SRPM_REGEX):
        rpmset.add(rpm)
    
    if len(rpmset) == 0:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        for rpm in self.cvars['rpms-directory'].findpaths(
            glob=glob, nregex=SRPM_REGEX):
          rpmset.add(rpm)
        if len(rpmset) == 0:
          raise RpmNotFoundError("missing release RPM(s)")
    return rpmset


EVENTS = {'INSTALLER': [ReleaseFilesEvent]}
