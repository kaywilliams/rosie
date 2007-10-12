from dims import filereader
from dims import pps

from dims.repocreator import YumRepoCreator

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event

from dimsbuild.modules.shared.rpms import ColorMixin, InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0

class ReleaseRpmEvent(Event, RpmBuildMixin, ColorMixin, InputFilesMixin):
  def __init__(self):
    self.gpg_dir     = P('/etc/pkg/rpm-gpg')
    self.repo_dir    = P('/etc/yum.repos.d')
    self.eula_dir    = P('/usr/share/eula')
    self.release_dir = P('/usr/share/doc/%s-release-%s' % (self.product, self.version))
    self.etc_dir     = P('/etc')
    self.eulapy_dir  = P('/usr/share/firstboot/modules')
    self.omf_dir     = P('/usr/share/omf/%s-release-notes' % self.product)
    self.html_dir    = P('/usr/share/doc/HTML')
    self.doc_dir     = P('/usr/share/doc/%s-release-notes-%s' % (self.product, self.version))

    self.installinfo = {
      'gpg'     : (None, self.gpg_dir),
      'repo'    : ('yum-repos', self.repo_dir),
      'eula'    : ('eula', self.eula_dir),
      'omf'     : ('release-notes/omf', self.omf_dir),
      'html'    : ('release-notes/html', self.html_dir),
      'doc'     : ('release-notes/doc', self.doc_dir),
      'release' : ('release-files', self.release_dir),
      'etc'     : (None, self.etc_dir),
      'eulapy'  : (None, self.eulapy_dir),
    }

    self.DATA = {
      'config':    ['*'],
      'variables': ['fullname', 'product', 'pva', 'cvars[\'web-path\']',
                    'cvars[\'gpgsign-public-key\']',],
      'input':     [],
      'output':    [],
    }

    Event.__init__(self, id='release-rpm',
                   requires=['source-vars', 'input-repos'],
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'],
                   conditionally_requires=['web-path', 'gpgsign-public-key',])
    RpmBuildMixin.__init__(self,
                           '%s-release' % self.product,
                           '%s release files created by dimsbuild' % self.fullname,
                           '%s release files' % self.product,
                           defobsoletes='fedora-release redhat-release centos-release '\
                           'fedora-release-notes redhat-release-notes centos-release-notes')
    InputFilesMixin.__init__(self)
    ColorMixin.__init__(self)

  def setup(self):
    self._setup_build()
    self._setup_download()

    self.setColors(prefix='#')
    # public gpg keys
    paths = []
    if self.cvars.get('gpgsign-public-key', None):
      paths.append(self.cvars.get('gpgsign-public-key'))
    for repo in self.cvars['repos'].values():
      for key in repo.gpgkeys:
        paths.append(key)

    self.io.setup_sync(self.build_folder/'gpg', paths=paths)

    # eulapy file
    paths = []
    include_firstboot = self.config.get('eula/include-in-firstboot/text()',
                                        'True') in BOOLEANS_TRUE
    eula_provided = self.config.get('eula/path/text()', None) is not None
    if include_firstboot and eula_provided:
      paths.append(self.SHARE_DIR/'release/eula.py')
    self.io.setup_sync(self.build_folder/'eulapy', paths=paths)

  def check(self):
    return self.release == '0' or \
           not self.autofile.exists() or \
           self.diff.test_diffs()

  def run(self):
    self.io.clean_eventcache(all=True)
    if self._test_build('True'):
      self._build_rpm()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    if not self._test_build('True'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []
    self.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))

  def _get_files(self):
    sources = {}
    sources.update(InputFilesMixin._get_files(self))
    return sources

  def _generate(self):
    "Create additional files."
    self.io.sync_input()
    for type in self.installinfo.keys():
      _, dir = self.installinfo[type]
      generator = '_generate_%s_files' % type
      if hasattr(self, generator):
        dest = self.rpmdir/dir.lstrip('/')
        getattr(self, generator)(dest)
    self._verify_release_notes()

  def _verify_release_notes(self):
    "Ensure the presence of RELEASE-NOTES.html and an index.html"
    rnotes = self.rpmdir.findpaths(glob='RELEASE-NOTES*')
    if len(rnotes) == 0:
      dir = self.rpmdir/self.html_dir.lstrip('/')
      dir.mkdirs()

      # create a default release notes file because none were found.
      import locale
      path = dir/('RELEASE-NOTES-%s.html' % locale.getdefaultlocale()[0])

      f = path.open('w')
      f.write(self.locals.release_html % {'bgcolor':   self.bgcolor,
                                          'textcolor': self.textcolor,
                                          'fullname':  self.fullname})
      f.close()
      path.chmod(0644)

      index_html = dir/'index.html'
      if not index_html.exists():
        path.link(index_html)
        index_html.chmod(0644)

  def _generate_etc_files(self, dest):
    dest.mkdirs()
    release_string = ['%s %s' %(self.fullname, self.version)]
    issue_string = ['Kernel \\r on an \\m\n']

    # write the product-release and redhat-release files
    filereader.write(release_string, dest/'redhat-release')
    filereader.write(release_string, dest/'%s-release' % self.product)

    # write the issue and issue.net files
    filereader.write(release_string+issue_string, dest/'issue')
    filereader.write(release_string+issue_string, dest/'issue.net')

    (dest/'redhat-release').chmod(0644)
    (dest/'%s-release' % self.product).chmod(0644)
    (dest/'issue').chmod(0644)
    (dest/'issue.net').chmod(0644)

  def _generate_repo_files(self, dest):
    dest.mkdirs() 
    self.repofile    = dest/'%s.repo' % self.product
    self.extra_repofile = dest/'extra.repo'    
    
    # create repo file for distribution, unless publish disabled
    if self.cvars['web-path']:
      path = self.cvars['web-path'] / 'os'
      lines = [ '[%s]' % self.product,
                'name=%s - %s' % (self.fullname, self.basearch),
                'baseurl=%s'   % path ]
      if self.cvars['gpgsign-public-key']:
        gpgkey = '%s/%s' % (path, P(self.cvars['gpgsign-public-key']).basename)
        lines.extend(['gpgcheck=1', 'gpgkey=%s' % gpgkey])
      else:
        lines.append('gpgcheck=0')
      filereader.write(lines, self.repofile)
    
    # create 'extra' repo file for input repos, if requested
    if self.config.get('yum-repos/@include-input', 'True') in BOOLEANS_TRUE:
      rc = YumRepoCreator(self.extra_repofile, self._config.file, '/distro/repos')
      rc.createRepoFile()
   

EVENTS = {'rpms': [ReleaseRpmEvent]}
