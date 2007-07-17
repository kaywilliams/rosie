from os.path import exists, join

import os

from dims import filereader

from dims.osutils     import basename, dirname, mkdir, find
from dims.sync        import sync
from dims.xmltree     import XmlPathError

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import EventInterface

from lib import ColorMixin, RpmsHandler, RpmsInterface

EVENTS = [
  {
    'id': 'release-rpm',
    'interface': 'ReleaseRpmInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS',
    'requires': ['source-vars'],
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
class ReleaseRpmHook(RpmsHandler, ColorMixin):
  
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
      'variables': ['interface.fullname',
                    'interface.product'],
      'input': [],
      'output': [],
    }
    
    #  Each key of the installinfo directionary is the name of the
    # directory in release RPM event's working directory and its value
    # tells the program what it should do with those files.
    #
    #  For example, self.installinfo['gpg'] are installed to
    # /etc/pki/rpm-gpg.
    installinfo = {
      'gpg'     : ('/distro/stores/*/store/gpgkey/text()',
                   interface.gpg_dir),
      'repo'    : ('/distro/rpms/release-rpm/yum-repos/path/text()',
                   interface.repo_dir),
      'eula'    : ('/distro/rpms/release-rpm/eula/path/text()',
                   interface.eula_dir),
      'omf'     : ('/distro/rpms/release-rpm/release-notes/omf/path/text()',
                   interface.omf_dir),
      'html'    : ('/distro/rpms/release-rpm/release-notes/html/path/text()',
                   interface.html_dir),
      'doc'     : ('/distro/rpms/release-rpm/release-notes/doc/path/text()',
                   interface.doc_dir),
      'release' : ('/distro/rpms/release-rpm/release-files/path/text()',
                   interface.release_dir),
      'etc'     : (None,
                   interface.etc_dir), 
      'eulapy'  : (None,
                   interface.eula_dir),
    }
    
    RpmsHandler.__init__(self, interface, data, 'release-rpm',
                         '%s-release' % interface.product,
                         summary='%s release files' % interface.fullname,
                         description='%s release files created by '
                                     'dimsbuild' % interface.fullname,
                         installinfo=installinfo)
    
    ColorMixin.__init__(self)
  
  def _generate(self):
    "Create additional files."
    for type in self.installinfo.keys():
      function = '_create_%s_files' %type
      if hasattr(self, function):
        getattr(self, function)()
    
    self._verify_release_notes()
  
  def _get_provides(self):
    obsoletes = self._get_obsoletes()
    if obsoletes:
      return ' '.join(['redhat-release', obsoletes])
    return 'redhat-release'
  
  def _get_obsoletes(self):
    packages = self.config.xpath('/distro/rpms/release-rpm/obsoletes/package/text()', [])
    if self.config.get('/distro/rpms/release-rpm/@use-default-set', 'True') in BOOLEANS_TRUE:
      packages.extend(['fedora-release', 'redhat-release', 'centos-release',
                       'fedora-release-notes', 'redhat-release-notes', 'centos-release-notes'])
    
    if packages:
      return ' '.join(packages)
    return None
    
  def _verify_release_notes(self):
    "Ensure the presence of RELEASE-NOTES.html and an index.html"
    rnotes = find(location=self.output_location, name='RELEASE-NOTES*')
    if len(rnotes) == 0:
      self.setColors(prefix='#')
      dir = join(self.output_location, 'html')
      if not exists(dir):
        mkdir(dir, parent=True)
      
      # create a default release notes file because none were found.
      import locale
      path = join(dir, 'RELEASE-NOTES-%s.html' % locale.getdefaultlocale()[0])
      
      f = open(path, 'w')      
      f.write(RELEASE_NOTES_HTML %(self.bgcolor, self.textcolor, self.fullname))
      f.close()
      
      index_html = join(self.output_location, 'html', 'index.html')
      if not exists(index_html):
        os.link(path, index_html)
  
  def _create_eulapy_file(self):
    if self.config.get('/distro/rpms/release-rpm/eula/include-in-firstboot/text()', 'True') in BOOLEANS_TRUE:
      if self.config.get('/distro/rpms/release-rpm/eula/path/text()', None) is not None:
        src = join(self.sharepath, 'release', 'eula.py')
        dst = join(self.output_location, 'eulapy')
        if not exists(dst):
          mkdir(dst, parent=True)
        sync(src, dst)
  
  def _create_etc_files(self):
    release_string = ['%s %s' %(self.fullname, self.version,)]
    issue_string = ['Kernel \\r on an \\m\n']
    
    etcdir = join(self.output_location, 'etc')
    if not exists(etcdir):
      mkdir(etcdir, parent=True)
      
    # write the product-release and redhat-release files
    filereader.write(release_string, join(etcdir, 'redhat-release'))
    filereader.write(release_string, join(etcdir, '%s-release' % self.product))
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, join(etcdir, 'issue'))
    filereader.write(release_string+issue_string, join(etcdir, 'issue.net'))


RELEASE_NOTES_HTML = '''<html>
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
'''
