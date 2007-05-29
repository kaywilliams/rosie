import os

import dims.filereader as filereader

from dims.osutils import basename, dirname, mkdir, find
from dims.repocreator import YumRepoCreator
from dims.sync import sync
from dims.xmltree import XmlPathError
from event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface import EventInterface
from lib import RpmHandler, RpmsInterface, getIpAddress
from main import BOOLEANS_TRUE
from os.path import exists, join
from output import tree

EVENTS = [
  {
    'id': 'release',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['release-rpm'],
    'parent': 'RPMS',
  },    
]

#------ HOOK FUNCTIONS ------#
def prerelease_hook(interface):
  handler = ReleaseRpmHandler(interface)
  interface.add_handler('release', handler)
  interface.disableEvent('release')
  if handler.pre() or (interface.eventForceStatus('release') or False):
    interface.enableEvent('release')
        
def release_hook(interface):
  interface.log(0, "creating release rpm")
  handler = interface.get_handler('release')
  handler.modify()

def postrelease_hook(interface):
  handler = interface.get_handler('release')
  if handler.create:
    # add rpms to the included-packages control var, so that
    # they are added to the comps.xml
    interface.append_cvar('included-packages', [handler.rpmname])    
    # add rpms to the excluded-packages control var, so that
    # they are removed from the comps.xml
    interface.append_cvar('excluded-packages', handler.obsoletes.split())

#---------- HANDLERS -------------#
class ReleaseRpmHandler(RpmHandler):
  def __init__(self, interface):
    # expand the xpath queries in the data struct
    data = {
      'config': [
        '//main/fullname/text()',
        '//main/version/text()',
        '//release-rpm',    
        '//stores/*/store/gpgkey',
        '//gpgkey',
      ],
      'input': [
        interface.config.mget('//release-rpm/yum-repos/path/text()', []),
        interface.config.mget('//release-rpm/eula/path/text()', []),
        interface.config.mget('//release-rpm/release-notes/path/text()', []),
        interface.config.mget('//release-rpm/release-files/path/text()', []),
        interface.config.mget('//stores/*/store/gpgkey/text()', []),
        interface.config.mget('//gpgkey/public/text()', []),
      ],
      'output': [
        join(interface.getMetadata(), 'release-rpm'),
      ],
    }

    RpmHandler.__init__(self, interface, data,
                        elementname='release-rpm',
                        rpmname='%s-release' %(interface.product,),
                        provides_test='redhat-release',
                        provides='redhat-release',
                        obsoletes = 'fedora-release redhat-release '
                                    'centos-release redhat-release-notes '
                                    'fedora-release-notes '
                                    'centos-release-notes',
                        description='%s release files' %(interface.fullname,),
                        long_description='%s release files created by dimsbuild' %(interface.fullname,))
    
    self.prefix = dirname(self.software_store) # prefix to the directories in data['output']    
    if not exists(self.software_store):
      mkdir(self.software_store, parent=True)

  def getInput(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)
    # sync the gpg keys to gpg/
    self._sync_gpg_keys()
    # sync eula files to eula/
    self._sync_eula_files()
    # sync release-notes to release-notes/
    self._sync_release_notes()
    # sync release-files files to release/
    self._sync_release_files()
    # sync .repo files to repos/
    self._sync_repos()

  def generate(self):
    self._generate_repos() # modify self.repos_files and self.repos_data
    self._generate_etc_files() # set self.etc_files and self.etc_data

  def _sync_gpg_keys(self):
    # sets the following variables:
    #   self.gpg_files : the list of gpgkeys, with paths relative to builddata/release-rpm
    #   self.gpg_data  : the string corresponding to the files, to be added to setup.cfg
    gpg_dir = join(self.output_location, 'gpg')
    mkdir(gpg_dir)
    gpgkeys = []
    if self.config.get('//gpgkey/sign/text()', 'False') in BOOLEANS_TRUE:
      gpg_key = self.config.eget('//gpgkey/public/text()', None)
      if gpg_key is None:
        raise Exception, "no public gpg key specified"
      gpgkeys.append(gpg_key)

    gpgkeys.extend(self.config.emget('//stores/*/store/gpgkey/text()', []))

    for gpgkey in gpgkeys:
      sync(gpgkey, gpg_dir)
    files = os.listdir(gpg_dir)
    if files:      
      self.gpg_files = map(lambda x: join('gpg', x), files)
      self.gpg_data = ''.join(['/etc/pki/rpm-gpg : ', ', '.join(self.gpg_files)])
    else:
      self.gpg_files = []
      self.gpg_data = ''

  def _sync_repos(self):
    # sets the following variables:
    #   self.repos_files : the list of .repo files, paths relative to builddata/release-rpm
    #   self.repos_data  : the string that needs to be added to setup.cfg's data_files option
    self._sync_files('yum-repos', '/etc/yum.repos.d', dirname='repos')
    
  def _sync_eula_files(self):
    # sets the following variables:
    #   self.eula_files : the list of eula files
    #   self.eula_data  : the string that needs to be added to setup.cfg's data_files option 
    self._sync_files('eula', '/usr/share/eula')
    
    if self.config.get('//release-rpm/eula/include-in-firstboot/text()', 'True') in BOOLEANS_TRUE and \
           self.config.get('//release-rpm/eula/path/text()', None) is not None:
      source = join(self.share_path, 'release', 'eula.py')
      sync(source, join(self.output_location, 'eula'))
      self.eulapy_data = '/usr/share/firstboot/modules : eula/eula.py'
      self.eulapy_files = ['eula/eula.py']
    else:
      self.eulapy_data = ''
      self.eulapy_files = []

  def _sync_release_notes(self):
    # sets the following variables:
    #   self.rnotes_doc_files : the list of release notes files to be installed in share/doc
    #   self.rnotes_doc_data  : the string that needs to be added to setup.cfg's data_files option
    #
    #   self.rnotes_omf_files : the list of release notes files to be installed in share/omf
    #   self.rnotes_omf_data  : the string that needs to be added to setup.cfg's data_files option    
    self._sync_files('release-notes', '/usr/share/doc/%s-release-notes-%s' %(self.product,
                                                                             self.version),
                     dirname='rnotes-doc', triage=lambda x: not x.endswith('omf'))
    self._sync_files('release-notes', '/usr/share/doc/%s-release-notes' %(self.product,),
                     dirname='rnotes-omf', triage=lambda x: x.endswith('omf'))

  def _sync_release_files(self):
    # sets the following variables:
    #   self.release_files : the list of release files installed at share/doc/prod-release/
    #   self.release_data  : the string that needs to be added to setup.cfg's data_files option    
    self._sync_files('release-files', '/usr/share/doc/%s-release-%s' %(self.product, self.version,),
                     dirname='release')

  def _generate_repos(self):
    if self.config.get('//%s/yum-repos/publish-repo/include/text()' %(self.elementname,), 'True') \
                       in BOOLEANS_TRUE:
      repofile = join(self.output_location, 'repos', '%s.repo' %(self.product,))
      authority = self.config.get('//%s/publish-repo/authority/text()' %(self.elementname,),
                                  ''.join(['http://', getIpAddress()]))
      path = join(self.config.get('//main/publishpath/text()', 'open_software'),
                  self.product, self.version, self.arch, 'os')
      lines = [
        '[%s]' %(self.product,),
        'name=%s %s - %s' %(self.fullname, self.version, self.arch,),
        'baseurl=%s' %(join(authority, path),),
        ]
      if self.config.get('//gpgkey/sign/text()', 'False') in BOOLEANS_TRUE:
        gpgkey = self.config.get('//gpgkey/public/text()')
        lines.extend(['gpgcheck=1', 'gpgkey=%s' %(gpgkey,)])
      else:
        lines.append('gpgcheck=0')
      filereader.write(lines, repofile)
      if self.repos_files:
        self.repos_files.append(repofile)
        self.repos_data = ', '.join([self.repos_data, join('repos', '%s.repo' %(self.product,))])
      else:
        file = join('repos', '%s.repo' %(self.product,))
        self.repos_files = [file]
        self.repos_data = '/etc/yum.repos.d : %s' %(file,)
        
    if self.config.get('//%s/yum-repos/input-repo/include/text()' %(self.elementname,), 'False') \
                       in BOOLEANS_TRUE:
      # create the source.repo
      repofile = join(self.output_location, 'repos', 'source.repo')
      rc = YumRepoCreator(repofile, self.config.file, '//sources')
      rc.createRepoFile()
      if self.repos_files:
        self.repos_files.append(repofile)
        self.repos_data = ', '.join([self.repos_data, join('repos', 'source.repo')])
      else:
        file = join('repos', 'source.repo')
        self.repos_files = [file]
        self.repos_data = '/etc/yum.repos.d : %s' %(file,)

  def _generate_etc_files(self):
    release_string = ['%s %s' %(self.fullname, self.version,)]
    issue_string = ['Kernel \\r on an \\m\n']

    # write the product-release and redhat-release files
    filereader.write(release_string, join(self.output_location, 'redhat-release'))
    filereader.write(release_string, join(self.output_location, '%s-release' %(self.product,)))
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, join(self.output_location, 'issue'))    
    filereader.write(release_string+issue_string, join(self.output_location, 'issue.net'))

    self.etc_files = ['redhat-release', '%s-release' %(self.product,), 'issue', 'issue.net']
    self.etc_data = ''.join(['/etc : ', ', '.join(self.etc_files)])

  def get_data_files(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    for file in self.etc_files + self.eula_files + self.rnotes_doc_files + self.rnotes_omf_files + \
            self.release_files + self.gpg_files + self.repos_files + self.eulapy_files:
      f.write('%s\n' %(file,))
    f.close()
    return '\n'.join([self.etc_data, self.eula_data, self.rnotes_doc_data, 
                      self.rnotes_omf_data, self.release_data, self.gpg_data,
                      self.repos_data, self.eulapy_data])
    
  def _sync_files(self, element, installdir, dirname=None, triage=lambda x: True):
    if not dirname:
      dirname = element
    dest_dir = join(self.output_location, dirname)
    mkdir(dest_dir)
    
    for item in self.config.mget('//%s/%s/path/text()' %(self.elementname, element), []):
      sync(item, dest_dir)

    dirname = dirname.replace('-', '_')
    files = map(lambda x: join(dirname, x), filter(triage, os.listdir(dest_dir)))
    if files:
      setattr(self, '%s_files' %(dirname,), files)
      setattr(self, '%s_data' %(dirname,),
              ''.join(['%s : ' %(installdir,), ', '.join(files)]))
    else:
      setattr(self, '%s_data' %(dirname,), '')  # if no files found, self.<element> is an empty string
      setattr(self, '%s_files' %(dirname,), [])
