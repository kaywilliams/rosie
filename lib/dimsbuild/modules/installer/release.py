from os.path import exists, isdir, isfile, join

from dims import osutils

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib import ExtractMixin, RpmNotFoundError

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'release-files',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['software'],
    'conditional-requires': ['gpgsign'],
    'parent': 'INSTALLER',
  },      
]

HOOK_MAPPING = {
 'ReleaseHook':  'release-files',
 'ValidateHook': 'validate',
}    

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/installer/release-files',
                            schemafile='release-files.rng')


class ReleaseHook(ExtractMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-files'

    self.metadata_struct = {
      'config': ['/distro/installer/release-files'],
      'input' : [],
      'output': [],
    }
    
    ExtractMixin.__init__(self, interface, self.metadata_struct,
                          join(interface.METADATA_DIR, 'INSTALLER', 'release-files.md'))

  def setup(self):
    self.DATA['input'].extend(self.find_rpms())
    self.interface.setup_diff(self.mdfile, self.DATA)
    
  def clean(self):
    self.interface.log(0, "cleaning release-files event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "synchronizing release files")
    self.extract()

  def generate(self, working_dir):
    files = {}
    rtn = []    
    for path in self.config.xpath('/distro/installer/release-files/path', []):
      source = path.text
      dest = join(self.software_store, path.attrib['dest'])
      files[source] = dest
    if self.config.get('/distro/installer/release-files/include-in-tree/@use-default-set', 'True') \
           in BOOLEANS_TRUE:
      for default_item in ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README',
                           '*-RPM-GPG', 'RPM-GPG-KEY-*', 'RPM-GPG-KEY-beta',
                           'README-BURNING-ISOS-en_US.txt', 'RELEASE-NOTES-en_US.html']:
        for item in osutils.find(location=working_dir, name=default_item):    
          files[item] = self.software_store

    osutils.mkdir(self.interface.SOFTWARE_STORE, parent=True)
    for source in files.keys():
      dest = files[source]
      if isfile(source) and isdir(dest):
        rtn.append(join(dest, osutils.basename(source)))
      self.interface.copy(source, dest, link=True)
    return rtn

  def find_rpms(self):
    rpmnames = self.config.xpath('/distro/installer/release-files/package/text()',
                                ['%s-release' %(self.interface.product,)])
    rpms = []
    for rpmname in rpmnames:
      for rpm in osutils.find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(rpmname,),
                      nregex='.*[Ss][Rr][Cc]\.[Rr][Pp][Mm]'):
        if rpm not in rpms:
          rpms.append(rpm)

    if len(rpms) == 0:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        for rpm in osutils.find(self.interface.cvars['rpms-directory'], name=glob,
                        nregex='.*[Ss][Rr][Cc]\.[Rr][Pp][Mm]'):
          if rpm not in rpms:
            rpms.append(rpm)
        if len(rpms) == 0:
          raise RpmNotFoundError("missing release RPM(s)")
    return rpms    
