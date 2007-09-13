from dims import filereader
from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE

from dimsbuild.modules.rpms.lib    import ColorMixin, RpmBuildEvent
from dimsbuild.modules.rpms.locals import RELEASE_NOTES_HTML

P = pps.Path

API_VERSION = 5.0

class ReleaseRpmEvent(RpmBuildEvent, ColorMixin):
  def __init__(self):
    RpmBuildEvent.__init__(self,
      id = 'release-rpm',
      requires = ['source-vars', 'gpgsign-public-key', 'repos'],
    )

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
    
    self.DATA = {
      'config':    ['/distro/rpms/release-rpm'],
      'variables': ['fullname',
                    'product',
                    'cvars[\'gpgsign-public-key\']'],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.get_mdfile()
    
  def _setup(self):
    self.setup_diff(self.mdfile, self.DATA)
    installinfo = {
      'gpg'     : (None, self.gpg_dir),
      'repo'    : ('/distro/rpms/release-rpm/yum-repos/path', self.repo_dir),
      'eula'    : ('/distro/rpms/release-rpm/eula/path', self.eula_dir),
      'omf'     : ('/distro/rpms/release-rpm/release-notes/omf/path', self.omf_dir),
      'html'    : ('/distro/rpms/release-rpm/release-notes/html/path', self.html_dir),
      'doc'     : ('/distro/rpms/release-rpm/release-notes/doc/path', self.doc_dir),
      'release' : ('/distro/rpms/release-rpm/release-files/path', self.release_dir),
      'etc'     : (None, self.etc_dir), 
      'eulapy'  : (None, self.eula_dir),
    }
    
    kwargs = {}
    kwargs['release'] = self.config.get('/distro/rpms/release-rpm/release/text()', '0')
    
    kwargs['obsoletes'] = ''
    if self.config.pathexists('/distro/rpms/release-rpm/obsoletes/package/text()'):
      kwargs['obsoletes'] += ' '.join(self.config.xpath(
                             '/distro/rpms/release-rpm/obsoletes/package/text()'))
    if self.config.get('/distro/rpms/release-rpm/@use-default-set', 'True'):
      kwargs['obsoletes'] += 'fedora-release redhat-release centos-release '\
                             'fedora-release-notes redhat-release-notes centos-release-notes'
    kwargs['provides'] = kwargs['obsoletes']
    self.register('%s-release' % self.product,
                  '%s release files created by dimsbuild' % self.fullname,
                  '%s release files' % self.product,
                  installinfo=installinfo,
                  **kwargs)
    self.setColors(prefix='#')
    self.add_data()    
    
    # public gpg keys
    paths = []
    if self.cvars.get('gpgsign-public-key', None):
      paths.append(self.cvars.get('gpgsign-public-key'))
    for repo in self.cvars['repos'].values():
      for key in repo.gpgkeys:
        paths.append(key)
    
    self.setup_sync(self.build_folder/'gpg', paths=paths)
    
    # eulapy file
    paths = []
    if self.config.get(
         '/distro/rpms/release-rpm/eula/include-in-firstboot/text()', 'True'
       ) in BOOLEANS_TRUE:
      if self.config.get(
           '/distro/rpms/release-rpm/eula/path/text()', None
         ) is not None:
        paths.append(self.SHARE_DIR / 'release/eula.py')
        
    self.setup_sync(self.build_folder/'eulapy', paths=paths)
  
  def _run(self):
    self.remove_output(all=True)
    if not self.test_build('True'):
      return
    self.build_rpm()
    self.write_metadata()
  
  def _apply(self):
    if not self.test_build('True'):
      return
    self.check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []      
    self.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))
  
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
                                   self.fullname))
      f.close()
      
      index_html = self.build_folder/'html/index.html'
      if not index_html.exists():
        path.link(index_html)
  
  def _generate_etc_files(self, dest):
    dest.mkdirs()
    release_string = ['%s %s' %(self.fullname,
                                self.version)]
    issue_string = ['Kernel \\r on an \\m\n']
      
    # write the product-release and redhat-release files
    filereader.write(release_string, dest/'redhat-release')
    filereader.write(release_string, dest/'%s-release' % self.product)
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, dest/'issue')
    filereader.write(release_string+issue_string, dest/'issue.net')


EVENTS = {'RPMS': [ReleaseRpmEvent]}
