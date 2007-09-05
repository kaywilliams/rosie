from dims import filereader
from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib       import ColorMixin, RpmBuildHook, RpmsInterface
from rpmlocals import RELEASE_NOTES_HTML

P = pps.Path

EVENTS = [
  {
    'id':        'release-rpm',
    'interface': 'ReleaseRpmInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent':    'RPMS',
    'requires':  ['source-vars', 'gpgsign-public-key', 'repos'],
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
    
    self.gpg_dir     = P('/etc/pkg/rpm-gpg')
    self.repo_dir    = P('/etc/yum.repos.d')
    self.eula_dir    = P('/usr/share/eula')
    self.release_dir = P('/usr/share/doc/%s-release-%s' % (self.product, self.version))
    self.etc_dir     = P('/etc')
    self.eula_dir    = P('/usr/share/firstboot/modules')
    
    relpath = P('/distro/rpms/release-rpm/release-notes/%s/@install-path')
    self.omf_dir  = P(self.config.get(relpath % 'omf', None) or \
                    '/usr/share/omf/%s-release-notes' % self.product)
    self.html_dir = P(self.config.get(relpath % 'html', None) or \
                    '/usr/share/doc/HTML')
    self.doc_dir  = P(self.config.get(relpath % 'doc', None) or \
                    '/usr/share/doc/%s-release-notes-%s' % (self.product, self.version))
  

#---------- HOOKS -------------#
class ReleaseRpmHook(RpmBuildHook, ColorMixin):  
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-rpm'
    
    self.interface = interface

    self.DATA = {
      'config':    ['/distro/rpms/release-rpm'],
      'variables': ['fullname',
                    'product',
                    'cvars[\'gpgsign-public-key\']'],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.interface.METADATA_DIR/'RPMS/release-rpm.md'

    RpmBuildHook.__init__(self, 'release-rpm')
    ColorMixin.__init__(self)

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    installinfo = {
      'gpg'     : (None,
                   self.interface.gpg_dir),
      'repo'    : ('/distro/rpms/release-rpm/yum-repos/path',
                   self.interface.repo_dir),
      'eula'    : ('/distro/rpms/release-rpm/eula/path',
                   self.interface.eula_dir),
      'omf'     : ('/distro/rpms/release-rpm/release-notes/omf/path',
                   self.interface.omf_dir),
      'html'    : ('/distro/rpms/release-rpm/release-notes/html/path',
                   self.interface.html_dir),
      'doc'     : ('/distro/rpms/release-rpm/release-notes/doc/path',
                   self.interface.doc_dir),
      'release' : ('/distro/rpms/release-rpm/release-files/path',
                   self.interface.release_dir),
      'etc'     : (None,
                   self.interface.etc_dir), 
      'eulapy'  : (None,
                   self.interface.eula_dir),
    }
    
    kwargs = {}
    kwargs['release'] = self.interface.config.get('/distro/rpms/release-rpm/release/text()', '0')
    
    kwargs['obsoletes'] = ''
    if self.interface.config.pathexists('/distro/rpms/release-rpm/obsoletes/package/text()'):
      kwargs['obsoletes'] += ' '.join(self.interface.config.xpath(
                             '/distro/rpms/release-rpm/obsoletes/package/text()'))
    if self.interface.config.get('/distro/rpms/release-rpm/@use-default-set', 'True'):
      kwargs['obsoletes'] += 'fedora-release redhat-release centos-release '\
                             'fedora-release-notes redhat-release-notes centos-release-notes'
    kwargs['provides'] = kwargs['obsoletes']
    self.register('%s-release' % self.interface.product,
                  '%s release files created by dimsbuild' % self.interface.fullname,
                  '%s release files' % self.interface.product,
                  installinfo=installinfo,
                  **kwargs)
    self.setColors(prefix='#')
    self.add_data()    

    # public gpg keys
    paths = []
    if self.interface.cvars.get('gpgsign-public-key', None):
      paths.append(self.interface.cvars.get('gpgsign-public-key'))
    for repo in self.interface.cvars['repos'].values():
      for key in repo.gpgkeys:
        paths.append(key)
    
    self.interface.setup_sync(self.build_folder/'gpg', paths=paths)

    # eulapy file
    paths = []
    if self.interface.config.get(
         '/distro/rpms/release-rpm/eula/include-in-firstboot/text()', 'True'
       ) in BOOLEANS_TRUE:
      if self.interface.config.get(
           '/distro/rpms/release-rpm/eula/path/text()', None
         ) is not None:
        paths.append(self.interface.sharepath / 'release/eula.py')
        
    self.interface.setup_sync(self.build_folder/'eulapy', paths=paths)

  def run(self):
    self.interface.remove_output(all=True)
    if not self.test_build('True'):
      return
    self.build_rpm()
    self.interface.write_metadata()

  def apply(self):
    if not self.test_build('True'):
      return
    self.check_rpms()
    if not self.interface.cvars['custom-rpms-info']:
      self.interface.cvars['custom-rpms-info'] = []      
    self.interface.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))

  def generate(self):
    "Create additional files."
    for type in self.installinfo.keys():
      generator = '_generate_%s_files' % type
      if hasattr(self, generator):
        dest = self.build_folder/type
        getattr(self, generator)(dest)

    self._verify_release_notes()
    
  def _verify_release_notes(self):
    "Ensure the presence of RELEASE-NOTES.html and an index.html"
    rnotes = self.build_folder.findpaths(glob='RELEASE-NOTES*')
    if len(rnotes) == 0:
      dir = self.build_folder/'html'
      if not dir.exists():
        dir.mkdirs()
      
      # create a default release notes file because none were found.
      import locale
      path = dir/('RELEASE-NOTES-%s.html' % locale.getdefaultlocale()[0])
      
      f = path.open('w')
      f.write(RELEASE_NOTES_HTML %(self.bgcolor,
                                   self.textcolor,
                                   self.interface.fullname))
      f.close()
      
      index_html = self.build_folder/'html/index.html'
      if not index_html.exists():
        path.link(index_html)
  
  def _generate_etc_files(self, dest):
    dest.mkdirs()
    release_string = ['%s %s' %(self.interface.fullname,
                                self.interface.version)]
    issue_string = ['Kernel \\r on an \\m\n']
      
    # write the product-release and redhat-release files
    filereader.write(release_string, dest/'redhat-release')
    filereader.write(release_string, dest/'%s-release' % self.interface.product)
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, dest/'issue')
    filereader.write(release_string+issue_string, dest/'issue.net')
