"""
Creates the release RPM.

To add more files to the release RPM, four things should be done:

1. set an instance variable that is a list of files to install
2. set an instance variable that is a string that looks as follows:
   <install directory>: <comma-separated list of files to install>
3. add the first variable to list in create_manifest()
4. add the second variable to the list in get_data_files()

You can use the _sync_files() function to do the first two of the four
steps.
"""

import os

import dims.filereader as filereader

from dims.osutils     import basename, dirname, mkdir, find
from dims.repocreator import YumRepoCreator
from dims.sync        import sync
from dims.xmltree     import XmlPathError
from event            import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface        import EventInterface
from lib              import ColorMixin, RpmHandler, RpmsInterface, getIpAddress
from main             import BOOLEANS_TRUE
from os.path          import exists, join
from output           import tree

EVENTS = [
  {
    'id': 'release-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['release-rpm'],
    'parent': 'RPMS',
  },    
]

HOOK_MAPPING = {
  'ReleaseRpmHook': 'release-rpm',
}

API_VERSION = 4.0

#---------- HANDLERS -------------#
class ReleaseRpmHook(RpmHandler, ColorMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-rpm'
    self.eventid = 'release-rpm'
    
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
        join(interface.METADATA_DIR, 'release-rpm'),
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
    ColorMixin.__init__(self, join(self.interface.METADATA_DIR,
                                   '%s.pkgs' %(self.interface.getBaseStore(),)))
    
    self.prefix = dirname(self.software_store) # prefix to the directories in data['output']    
    if not exists(self.software_store):
      mkdir(self.software_store, parent=True)

  def run(self):
    self.set_colors()
    RpmHandler.run(self)
      
  def get_input(self):
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
    self._verify_release_notes()

  def create_manifest(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')    
    for item in ['etc_files', 'eula_files', 'rnotes_doc_files', 'rnotes_omf_files',
                 'rnotes_html_files', 'release_files', 'gpg_files', 'repos_files',
                 'eulapy_files', 'default_rnotes_files']:
      if hasattr(self, item):
        for file in getattr(self, item):          
          f.write('%s\n' %(file,))
    f.close()
    
  def get_data_files(self):
    data_value = None
    for data in ['etc_data', 'eula_data', 'rnotes_doc_data', 'rnotes_omf_data', 'rnotes_html_data',
                 'release_data', 'gpg_data', 'repos_data', 'eulapy_data', 'default_rnotes_data']:
      if hasattr(self, data):
        value = getattr(self, data)
        if data_value is None:
          data_value = value
        else:
          data_value = '\n'.join([data_value, value])
    return data_value

  def _verify_release_notes(self):
    rnotes = find(location=self.output_location, name='RELEASE-NOTES*')
    if len(rnotes) == 0:
      # create a default release notes file because none were found.
      import locale
      rnotename = 'RELEASE-NOTES-%s.html' %(locale.getdefaultlocale()[0],) 
      path = join(self.output_location, rnotename)
      f = open(path, 'w')      
      f.write("""<html>
        <head>
        <style type="text/css">
          <!--
          body {
            background-color: %s;
            color: %s;
            font-family: sans-serif;
          }
          .center {
            text-align: center;
          }
          p {
            margin-top: 20%%;
          }
          -->
        </style>
        </head>
        <body>
          <h1>
            <p class="center">Welcome to %s!</p>
          </h1>
        </body>
      </html>
      """ %(self.bgcolor.replace('0x', '#'), self.textcolor.replace('0x', '#'), self.fullname,))
      f.close()
      index_html = join(self.output_location, 'index.html')
      os.link(path, index_html)
      self.default_rnotes_files = [rnotename, 'index.html']
      self.default_rnotes_data = "/usr/share/doc/HTML/: %s, index.html" %(rnotename,)
      
  def _sync_gpg_keys(self):
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

  def _sync_repos(self):
    self._sync_files('yum-repos', '/etc/yum.repos.d', dirname='repos')
    
  def _sync_eula_files(self):
    self._sync_files('eula', '/usr/share/eula')
    
    if self.config.get('//release-rpm/eula/include-in-firstboot/text()', 'True') in BOOLEANS_TRUE and \
           self.config.get('//release-rpm/eula/path/text()', None) is not None:
      source = join(self.share_path, 'release', 'eula.py')
      sync(source, join(self.output_location, 'eula'))
      self.eulapy_data = '/usr/share/firstboot/modules : eula/eula.py'
      self.eulapy_files = ['eula/eula.py']

  def _sync_release_notes(self):
    for element, path, dirname in \
            [('release-notes/omf', '/usr/share/omf/%s-release-notes' %(self.product,), 'rnotes-omf'),
             ('release-notes/html', '/usr/share/doc/HTML', 'rnotes-html'),
             ('release-notes/doc', '/usr/share/doc/%s-release-notes-%s'
              %(self.product, self.version,), 'rnotes-doc')]:
      installpath = self.config.get('//%s/%s/@install-path' %(self.elementname, element,), path)      
      self._sync_files(element, installpath, dirname=dirname)

  def _sync_release_files(self):
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
      if hasattr(self, 'repos_files'):
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
    
  def _sync_files(self, element, installdir, dirname=None, triage=lambda x: True):
    if not dirname:
      dirname = element
    dest_dir = join(self.output_location, dirname)
    mkdir(dest_dir)
    
    for item in self.config.mget('//%s/%s/path/text()' %(self.elementname, element), []):
      sync(item, dest_dir)

    variable_prefix = dirname.replace('-', '_')
    files = map(lambda x: join(dirname, x), filter(triage, os.listdir(dest_dir)))
    if files:
      setattr(self, '%s_files' %(variable_prefix,), files)
      setattr(self, '%s_data' %(variable_prefix,),
              ''.join(['%s : ' %(installdir,), ', '.join(files)]))
