from os.path          import exists, join

import os

from dims.osutils     import basename, dirname, mkdir, find
from dims.repocreator import YumRepoCreator
from dims.sync        import sync
from dims.xmltree     import XmlPathError

import dims.filereader as filereader

from event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from interface import EventInterface
from main      import BOOLEANS_TRUE, tree

from rpms.lib import ColorMixin, RpmsHandler, RpmsInterface, getIpAddress

EVENTS = [
  {
    'id': 'release-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS',
  },    
]

HOOK_MAPPING = {
  'ReleaseRpmHook': 'release-rpm',
}

API_VERSION = 4.0

#---------- HANDLERS -------------#
class ReleaseRpmHook(RpmsHandler, ColorMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-rpm'
    self.eventid = 'release-rpm'
    
    data = {
      'config': [
        '//main/fullname/text()',
        '//main/version/text()',
        '//release-rpm',    
        '//stores/*/store/gpgkey',
        '//gpgsign',
      ],      
      'input': [
        interface.config.xpath('//release-rpm/yum-repos/path/text()', []),
        interface.config.xpath('//release-rpm/eula/path/text()', []),
        interface.config.xpath('//release-rpm/release-notes/path/text()', []),
        interface.config.xpath('//release-rpm/release-files/path/text()', []),
        interface.config.xpath('//stores/*/store/gpgkey/text()', []),
        interface.config.xpath('//gpgsign/public/text()', []),
      ],
      'output': [
        join(interface.METADATA_DIR, 'release-rpm'),
      ],
    }

    RpmsHandler.__init__(self, interface, data,
                         elementname='release-rpm',
                         rpmname='%s-release' %(interface.product,),
                         description='%s release files' %(interface.fullname,),
                         long_description='%s release files created by dimsbuild' %(interface.fullname,))
    
    ColorMixin.__init__(self, join(self.interface.METADATA_DIR,
                                   '%s.pkgs' %(self.interface.getBaseStore(),)))

    # self.installdirs is a (key:value) mapping with the key the name
    # of a variable in self's scope -- the self.variable is a list of files --
    # and the value of it is the directory to which those files should be installed
    #
    # To add more files to the release rpm, do the following:
    #  1. add an entry to this dictionary, with the name of the variable that holds
    #     a list of files as the key and the value being the directory to which those
    #     files should be installed.
    #  2. create a function that sets up the variable; self._sync_files() might come in
    #     in handy.
    #
    # For example, self.etcfiles is a variable that holds a list of files that are
    # installed to the /etc location.
    self.installdirs = {
      'default_rnotes': '/usr/share/doc/HTML',
      'etcfiles':       '/etc',
      'eulafiles':      '/usr/share/eula',
      'eulapy':         '/usr/share/firstboot/modules',
      'gpgfiles':       '/etc/pki/rpm-gpg',
      'releasefiles':   '/usr/share/doc/%s-release-%s' %(self.product, self.version,),
      'reposfiles':     '/etc/yum.repos.d',
      'rnotes_doc':     '/usr/share/doc/%s-release-notes-%s' %(self.product, self.version,),
      'rnotes_html':    '/usr/share/doc/HTML',
      'rnotes_omf':     '/usr/share/omf/%s-release-notes' %(self.product,),
    }
    
  def get_input(self):
    if not exists(self.rpm_output):
      mkdir(self.rpm_output, parent=True)
    if not exists(self.output_location):
      mkdir(self.output_location, parent=True)

  def generate(self):
    self._process_gpg_keys()
    self._process_eula_files()
    self._process_release_notes()
    self._process_release_files()
    self._process_repos()
    self._process_etc_files()
    self._verify_release_notes()

  def create_manifest(self):
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    for item in self.installdirs.keys():
      if hasattr(self, item):
        files = getattr(self, item)
        if files:
          for file in files:
            f.write('%s\n' %(file,))
    f.close()
    
  def get_data_files(self):
    data = None
    for key in self.installdirs.keys():
      if hasattr(self, key):
        files = getattr(self, key)
        if files:
          datum = '%s : %s' %(self.installdirs[key], ', '.join(files))
          if data is None:
            data = datum
          else:
            data = '\n\t'.join([data, datum])
    return data

  def get_provides(self):
    return 'redhat-release'

  def get_obsoletes(self):
    packages = self.config.xpath('//rpms/release-rpm/obsoletes/package/text()', [])
    if self.config.get('//rpms/release-rpm/@use-default-set', 'True') in BOOLEANS_TRUE:
      packages.extend(['fedora-release', 'redhat-release', 'centos-release',
                       'fedora-release-notes', 'redhat-release-notes', 'centos-release-notes'])

    if packages:
      return ' '.join(packages)
    return None
      
  def _verify_release_notes(self):
    rnotes = find(location=self.output_location, name='RELEASE-NOTES*')
    if len(rnotes) == 0:
      self.set_colors()      
      # create a default release notes file because none were found.
      import locale
      rnotename = 'RELEASE-NOTES-%s.html' %(locale.getdefaultlocale()[0],) 
      path = join(self.output_location, rnotename)
      f = open(path, 'w')      
      f.write(RELEASE_NOTES_HTML %(self.bgcolor.replace('0x', '#'),
                                   self.textcolor.replace('0x', '#'),
                                   self.fullname,))
      f.close()
      self.default_rnotes = [rnotename]
      index_html = join(self.output_location, 'index.html')
      if not exists(index_html):
        os.link(path, index_html)
        self.default_rnotes.append('index.html')
      
  def _process_gpg_keys(self):
    # sets self.gpgfiles and self.gpgdata    
    gpgdir = join(self.output_location, 'gpg')
    mkdir(gpgdir)
    gpgkeys = []

    if self.config.get('//gpgsign/sign/text()', 'False') in BOOLEANS_TRUE:      
      gpgkey = self.config.get('//gpgkey/public/text()', None)
      if gpgkey is not None:
        gpgkeys.append(gpgkey)

    gpgkeys.extend(self.config.xpath('//stores/*/store/gpgkey/text()', []))

    for gpgkey in gpgkeys:
      sync(gpgkey, gpg_dir)

    self.gpgfiles = [join('gpg', x) for x in os.listdir(gpgdir)]

  def _process_repos(self):
    self._sync_files('yum-repos', 'reposfiles', dirname='repos')
    reposdir = join(self.output_location, 'repos')
    
    extrarepos = []
    if self.config.get('//%s/yum-repos/publish-repo/include/text()' %(self.elementname,), 'True') in BOOLEANS_TRUE:      
      repofile = join(reposdir, '%s.repo' %(self.product,))
      authority = self.config.get('//%s/publish-repo/authority/text()' %(self.elementname,),
                                  ''.join(['http://', getIpAddress()]))
      path = join(self.config.get('//main/publishpath/text()', 'open_software'),
                  self.product, self.version, self.arch, 'os')
      lines = ['[%s]' %(self.product,),
               'name=%s %s - %s' %(self.fullname, self.version, self.arch,),
               'baseurl=%s' %(join(authority, path),)]
      
      if self.config.get('//gpgsign/sign/text()', 'False') in BOOLEANS_TRUE:
        gpgkey = self.config.get('//gpgsign/public/text()')
        lines.extend(['gpgcheck=1', 'gpgkey=%s' %(gpgkey,)])
      else:
        lines.append('gpgcheck=0')
        
      filereader.write(lines, repofile)
      extrarepos.append(join('repos', '%s.repo' %(self.product,)))

    if self.config.get('//%s/yum-repos/input-repo/include/text()' %(self.elementname,), 'False') in BOOLEANS_TRUE:
      repofile = join(reposdir, 'source.repo')
      rc = YumRepoCreator(repofile, self.config.file, '//stores')
      rc.createRepoFile()
      extrarepos.append(join('repos', 'source.repo'))

    for repo in self.config.xpath('//%s/yum-repos/path/text()' %(self.elementname,), []):
      sync(repo, reposdir)
      extrarepos.append(repo)
      
    if hasattr(self, 'reposfiles'):
      self.reposfiles.extend(extrarepos)
    else:
      self.reposfiles = extrarepos
    
  def _process_eula_files(self):
    self._sync_files('eula', 'eulafiles', dirname='eula')
    if self.config.get('//%s/eula/include-in-firstboot/text()' %(self.elementname,), 'True') in BOOLEANS_TRUE and \
           self.config.get('//%s/eula/path/text()' %(self.elementname,), None) is not None:
      source = join(self.sharepath, 'release', 'eula.py')
      sync(source, join(self.output_location, 'eula'))
      self.eulapyfiles = ['eula/eula.py']

  def _process_release_notes(self):
    # rnotes is a list of 3-tuples: (xpath query relative to release-rpm, variable name)
    rnotes = [('release-notes/omf',  'rnotes_omf'),
              ('release-notes/html', 'rnotes_html'),
              ('release-notes/doc',  'rnotes_doc')]

    for element, variable in rnotes:
      installpath = self.config.get('//%s/%s/@install-path' %(self.elementname, element), None)
      if installpath is not None:
        self.installdirs[variable] = installpath
      self._sync_files(element, variable)

  def _process_release_files(self):
    self._sync_files('release-files', 'release')

  def _process_etc_files(self):
    release_string = ['%s %s' %(self.fullname, self.version,)]
    issue_string = ['Kernel \\r on an \\m\n']

    # write the product-release and redhat-release files
    filereader.write(release_string, join(self.output_location, 'redhat-release'))
    filereader.write(release_string, join(self.output_location, '%s-release' %(self.product,)))
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, join(self.output_location, 'issue'))    
    filereader.write(release_string+issue_string, join(self.output_location, 'issue.net'))

    self.etcfiles = ['redhat-release', '%s-release' %(self.product,), 'issue', 'issue.net']
    
  def _sync_files(self, element, variable, dirname=None, triage=lambda x: True):
    dirname = dirname or variable
    destdir = join(self.output_location, dirname)
    if not exists(destdir):
      mkdir(destdir)
    
    for item in self.config.xpath('//%s/%s/path/text()' %(self.elementname, element), []):
      sync(item, destdir)

    files = map(lambda x: join(dirname, x), filter(triage, os.listdir(destdir)))
    if files:
      setattr(self, variable, files)


RELEASE_NOTES_HTML = """<html>
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
"""
