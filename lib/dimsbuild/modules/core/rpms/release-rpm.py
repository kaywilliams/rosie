from dims import pps

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.event     import Event

from dimsbuild.modules.shared import ColorMixin, InputFilesMixin, RpmBuildMixin

P = pps.Path

API_VERSION = 5.0
EVENTS = {'rpms': ['ReleaseRpmEvent']}

class ReleaseRpmEvent(Event, RpmBuildMixin, ColorMixin, InputFilesMixin):
  def __init__(self):
    Event.__init__(self, id='release-rpm',
                   requires=['source-vars', 'input-repos', 'release-versions'],
                   provides=['custom-rpms', 'custom-srpms', 'custom-rpms-info'],
                   conditionally_requires=['web-path', 'gpgsign-public-key',])
    RpmBuildMixin.__init__(self,
                           '%s-release' % self.product,
                           '%s release files created by dimsbuild' % self.fullname,
                           '%s release files' % self.product,
                           default_obsoletes=['fedora-release', 'redhat-release', 'centos-release',
                           'fedora-release-notes', 'redhat-release-notes', 'centos-release-notes'])
    InputFilesMixin.__init__(self)
    ColorMixin.__init__(self)

    self.doc_dir = P('/usr/share/doc/%s-release-notes-%s' % (self.product, self.version))
    self.etc_dir = P('/etc')
    self.eula_dir = P('/usr/share/eula')
    self.eulapy_dir = P('/usr/share/firstboot/modules')
    self.gpg_dir = P('/etc/pkg/rpm-gpg')
    self.html_dir = P('/usr/share/doc/HTML')
    self.omf_dir = P('/usr/share/omf/%s-release-notes' % self.product)
    self.release_dir = P('/usr/share/doc/%s-release-%s' % (self.product, self.version))
    self.repo_dir = P('/etc/yum.repos.d')

    self.build_folder = self.mddir / 'build'

    self.installinfo = {
      'gpg'     : (None, self.gpg_dir, None),
      'repo'    : ('yum-repos/path', self.repo_dir, None),
      'eula'    : ('eula/path', self.eula_dir, None),
      'omf'     : ('release-notes/omf/path', self.omf_dir, None),
      'html'    : ('release-notes/html/path', self.html_dir, None),
      'doc'     : ('release-notes/doc/path', self.doc_dir, None),
      'release' : ('release-files/path', self.release_dir, None),
      'etc'     : (None, self.etc_dir, None),
      'eulapy'  : (None, self.eulapy_dir, None),
    }

    self.DATA = {
      'config':    ['*'],
      'variables': ['fullname', 'product', 'pva', 'cvars[\'web-path\']',
                    'cvars[\'gpgsign-public-key\']',],
      'input':     [],
      'output':    [self.build_folder],
    }

  def setup(self):
    obsoletes = [ '%s %s %s' %(n,e,v)
                  for n,e,v in self.cvars.get('release-versions', [])]
    provides = [ '%s %s %s' % (n,e,v)
                 for _,e,v in self.cvars.get('release-versions', [])]
    provides.extend( [ 'redhat-release %s %s' % (e,v)
                       for _,e,v in self.cvars.get('release-versions', [])])
    self._setup_build(obsoletes=obsoletes, provides=provides)
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
      for path in self.SHARE_DIRS:
        path = path/'release/eula.py'
        if path.exists():
          paths.append(path); break
      self.io.setup_sync(self.build_folder/'eulapy', paths=paths)

  def check(self):
    return self.rpm_release == '0' or \
           not self.autofile.exists() or \
           self.diff.test_diffs()

  def run(self):
    self.io.clean_eventcache(all=True)
    self._build_rpm()
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self._check_rpms()
    self.cvars.setdefault('custom-rpms-info', []).append(
      (self.rpm_name, 'mandatory', None, self.rpm_obsoletes, None)
    )

  def _get_files(self):
    sources = {}
    sources.update(InputFilesMixin._get_files(self))
    return sources

  def _generate(self):
    "Create additional files."
    self.io.sync_input(cache=True)
    for type in self.installinfo.keys():
      _, dir, _ = self.installinfo[type]
      generator = '_generate_%s_files' % type
      if hasattr(self, generator):
        dest = self.rpm_dir/dir.lstrip('/')
        getattr(self, generator)(dest)
    self._verify_release_notes()

  def _verify_release_notes(self):
    "Ensure the presence of RELEASE-NOTES.html and an index.html"
    rnotes = self.rpm_dir.findpaths(glob='RELEASE-NOTES*')
    if len(rnotes) == 0:
      dir = self.rpm_dir/self.html_dir.lstrip('/')
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
    (dest/'redhat-release').write_lines(release_string)
    (dest/'%s-release' % self.product).write_lines(release_string)

    # write the issue and issue.net files
    (dest/'issue').write_lines(release_string + issue_string)
    (dest/'issue.net').write_lines(release_string + issue_string)

    (dest/'redhat-release').chmod(0644)
    (dest/'%s-release' % self.product).chmod(0644)
    (dest/'issue').chmod(0644)
    (dest/'issue.net').chmod(0644)

  def _generate_repo_files(self, dest):
    dest.mkdirs()
    repofile = dest/'%s.repo' % self.product

    if self.config.get('yum-repos/@create-base', 'True') in BOOLEANS_TRUE \
           and self.cvars['web-path']:
      path = self.cvars['web-path'] / 'os'
      lines = [ '[%s]' % self.product,
                'name=%s - %s' % (self.fullname, self.basearch),
                'baseurl=%s'   % path ]
      if self.cvars['gpgsign-public-key']:
        gpgkey = '%s/%s' % (path, P(self.cvars['gpgsign-public-key']).basename)
        lines.extend(['gpgcheck=1', 'gpgkey=%s' % gpgkey])
      else:
        lines.append('gpgcheck=0')
      repofile.write_lines(lines)
