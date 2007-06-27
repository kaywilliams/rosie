from os.path import exists, isdir, isfile, join

from dims.osutils import basename, find, mkdir, rm
from dims.sync    import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib import ExtractHandler, RpmNotFoundError

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'installer-release-files',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'requires': ['software'],
    'conditional-requires': ['gpgsign'],
    'parent': 'INSTALLER',
  },      
]

HOOK_MAPPING = {
 'InstallerReleaseHook': 'installer-release-files',
 'ValidateHook':         'validate',
}    

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer_release.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('//installer/release-files', schemafile='installer-release-files.rng')


class InstallerReleaseHook(ExtractHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer_release.installer-release-files'

    self.metadata_struct = {
      'config': ['//installer/release-files'],
      'input' : [],
      'output': [],
    }
    
    ExtractHandler.__init__(self, interface, self.metadata_struct,
                            join(interface.METADATA_DIR, 'installer-release-files.md'))
    
  def run(self):
    ExtractHandler.extract(self, "synchronizing installer release files")

  def generate(self):
    files = {}
    rtn = []    
    for path in self.config.xpath('//installer/release-files/path', []):
      source = path.text
      dest = join(self.software_store, path.attrib['dest'])
      files[source] = dest
    if self.config.get('//release-files/include-in-tree/@use-default-set', 'True') in BOOLEANS_TRUE:
      for default_item in ['eula.txt', 'beta_eula.txt', 'EULA', 'GPL', 'README',
                           '*-RPM-GPG', 'RPM-GPG-KEY-*', 'RPM-GPG-KEY-beta',
                           'README-BURNING-ISOS-en_US.txt', 'RELEASE-NOTES-en_US.html']:
        for item in find(location=self.working_dir, name=default_item):    
          files[item] = self.software_store

    mkdir(self.interface.SOFTWARE_STORE, parent=True)
    for source in files.keys():
      dest = files[source]
      if isfile(source) and isdir(dest):
        rtn.append(join(dest, basename(source)))
      sync(source, dest, link=True)
    return rtn

  def find_rpms(self):
    rpmnames = self.config.xpath('//installer/release-files/package/text()',
                                ['%s-release' %(self.interface.product,)])
    rpms = []
    for rpmname in rpmnames:
      for rpm in find(self.interface.cvars['rpms-directory'], name='%s-*-*' %(rpmname,),
                      nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]'):
        if rpm not in rpms:
          rpms.append(rpm)

    if len(rpms) == 0:
      for glob in ['*-release-*-[a-zA-Z0-9]*.[Rr][Pp][Mm]',
                   '*-release-notes-*-*']:
        for rpm in find(self.interface.cvars['rpms-directory'], name=glob,
                        nregex='.*[Ss][Rr][Cc][.][Rr][Pp][Mm]'):
          if rpm not in rpms:
            rpms.append(rpm)
        if len(rpms) == 0:
          raise RpmNotFoundError("missing release RPM(s)")
    return rpms    
