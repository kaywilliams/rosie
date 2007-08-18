from os.path import exists, join

import os

from dims import filereader
from dims import osutils
from dims import sync

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import EventInterface

from lib       import ColorMixin, RpmBuildHook, RpmsInterface
from rpmlocals import RELEASE_NOTES_HTML

EVENTS = [
  {
    'id':        'release-rpm',
    'interface': 'ReleaseRpmInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent':    'RPMS',
    'requires':  ['source-vars'],
  },    
]

HOOK_MAPPING = {
  'ReleaseRpmHook': 'release-rpm',
}

API_VERSION = 4.1

#---------- INTERFACES --------#
class ReleaseRpmInterface(RpmsInterface):
  def __init__(self, base):
    RpmsInterface.__init__(self, base)
    
    self.gpg_dir     = '/etc/pkg/rpm-gpg'
    self.repo_dir    = '/etc/yum.repos.d'
    self.eula_dir    = '/usr/share/eula'
    self.release_dir = '/usr/share/doc/%s-release-%s' % (self.product, self.version)
    self.etc_dir     = '/etc'
    self.eula_dir    = '/usr/share/firstboot/modules'
    
    relpath = '/distro/rpms/release-rpm/release-notes/%s/@install-path'
    self.omf_dir  = self.config.get(relpath % 'omf', None) or \
                    '/usr/share/omf/%s-release-notes' % self.product
    self.html_dir = self.config.get(relpath % 'html', None) or \
                    '/usr/share/doc/HTML'
    self.doc_dir  = self.config.get(relpath % 'doc', None) or \
                    '/usr/share/doc/%s-release-notes-%s' % (self.product, self.version)
  

#---------- HOOKS -------------#
class ReleaseRpmHook(RpmBuildHook, ColorMixin):  
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-rpm'
    
    self.interface = interface
    
    data = {
      'config': [
        '/distro/rpms/release-rpm',    
        '/distro/repos/repo/gpgkey',
        '/distro/gpgsign',
      ],
      'variables': ['fullname',
                    'product'],
      'input': [],
      'output': [],
    }
    
    # Each key of the installinfo directionary is the name of the
    # directory in release RPM event's working directory and its value
    # tells the program what it should do with those files.
    installinfo = {
      'gpg'     : (None,
                   interface.gpg_dir),
      'repo'    : ('/distro/rpms/release-rpm/yum-repos/path',
                   interface.repo_dir),
      'eula'    : ('/distro/rpms/release-rpm/eula/path',
                   interface.eula_dir),
      'omf'     : ('/distro/rpms/release-rpm/release-notes/omf/path',
                   interface.omf_dir),
      'html'    : ('/distro/rpms/release-rpm/release-notes/html/path',
                   interface.html_dir),
      'doc'     : ('/distro/rpms/release-rpm/release-notes/doc/path',
                   interface.doc_dir),
      'release' : ('/distro/rpms/release-rpm/release-files/path',
                   interface.release_dir),
      'etc'     : (None,
                   interface.etc_dir), 
      'eulapy'  : (None,
                   interface.eula_dir),
    }

    packages = self.interface.config.xpath(
      '/distro/rpms/release-rpm/obsoletes/package/text()', []
    )
    if interface.config.get('/distro/rpms/release-rpm/@use-default-set', 'True') \
           in BOOLEANS_TRUE:
      packages.extend(['fedora-release', 'redhat-release', 'centos-release',
                       'fedora-release-notes', 'redhat-release-notes',
                       'centos-release-notes'])
    if packages:
      obsoletes = ' '.join(packages)
    else:
      obsoletes = None

    provides = 'redhat-release'
    if obsoletes:
      provides = provides + obsoletes
      
    RpmBuildHook.__init__(self, interface, data, 'release-rpm',
                          '%s-release' % interface.product,
                          summary='%s release files' % interface.fullname,
                          description='%s release files created by '
                          'dimsbuild' % interface.fullname,
                          installinfo=installinfo,
                          provides=provides,
                          obsoletes=obsoletes)
    
    ColorMixin.__init__(self)
    
  def generate(self):
    "Create additional files."
    for type in self.installinfo.keys():
      generator = '_generate_%s_files' % type
      if hasattr(self, generator):
        dest = join(self.build_folder, type)
        getattr(self, generator)(dest)

    self._verify_release_notes()
    
  def _verify_release_notes(self):
    "Ensure the presence of RELEASE-NOTES.html and an index.html"
    rnotes = osutils.find(location=self.build_folder, name='RELEASE-NOTES*')
    if len(rnotes) == 0:
      self.setColors(prefix='#')
      dir = join(self.build_folder, 'html')
      if not exists(dir):
        osutils.mkdir(dir, parent=True)
      
      # create a default release notes file because none were found.
      import locale
      path = join(dir, 'RELEASE-NOTES-%s.html' % locale.getdefaultlocale()[0])
      
      f = open(path, 'w')      
      f.write(RELEASE_NOTES_HTML %(self.bgcolor,
                                   self.textcolor,
                                   self.interface.fullname))
      f.close()
      
      index_html = join(self.build_folder, 'html', 'index.html')
      if not exists(index_html):
        os.link(path, index_html)

  def _generate_gpg_files(self, dest):
    if self.interface.cvars.get('gpg-public-key', None):
      osutils.mkdir(dest, parent=True)
      sync.sync(self.interface.cvars['gpg-public-key'], dest)
    for repo in self.interface.cvars['repos'].values():
      osutils.mkdir(dest, parent=True)      
      if repo.gpgkey:
        sync.sync(repo.gpgkey, dest)    
    
  def _generate_eulapy_files(self, dest):
    if self.interface.config.get(
         '/distro/rpms/release-rpm/eula/include-in-firstboot/text()', 'True'
       ) in BOOLEANS_TRUE:
      if self.interface.config.get(
           '/distro/rpms/release-rpm/eula/path/text()', None
         ) is not None:
        osutils.mkdir(dest, parent=True)
        src = join(self.interface.sharepath, 'release', 'eula.py')
        sync.sync(src, dest)
  
  def _generate_etc_files(self, dest):
    osutils.mkdir(dest, parent=True)
    release_string = ['%s %s' %(self.interface.fullname,
                                self.interface.version)]
    issue_string = ['Kernel \\r on an \\m\n']
      
    # write the product-release and redhat-release files
    filereader.write(release_string, join(dest, 'redhat-release'))
    filereader.write(release_string, join(dest, '%s-release' % \
                                          self.interface.product))
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, join(dest, 'issue'))
    filereader.write(release_string+issue_string, join(dest, 'issue.net'))
