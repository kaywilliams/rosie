from os.path import exists, join

import os

from dims import filereader

from dims.osutils     import basename, dirname, mkdir, find
from dims.repocreator import YumRepoCreator
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
    
  def getGpgDirectory(self):
    return '/etc/pkg/rpm-gpg'

  def getRepoDirectory(self):
    return '/etc/yum.repos.d'

  def getEulaDirectory(self):
    return '/usr/share/eula'

  def getOmfDirectory(self):
    return self.config.get('/distro/rpms/release-rpm/release-notes/omf/@install-path', None) or \
           '/usr/share/omf/%s-release-notes' % self.product

  def getHtmlDirectory(self):
    return self.config.get('/distro/rpms/release-rpm/release-notes/html/@install-path', None) or \
           '/usr/share/doc/HTML'

  def getDocDirectory(self):
    return self.config.get('/distro/rpms/release-rpm/release-notes/doc/@install-path', None) or \
           '/usr/share/doc/%s-release-notes-%s' %(self.product, self.version)

  def getReleaseDirectory(self):
    return '/usr/share/doc/%s-release-%s' %(self.product, self.version)

  def getEtcDirectory(self):
    return '/etc'

  def getEulaPyDirectory(self):
    return '/usr/share/firstboot/modules'
  

#---------- HOOKS -------------#
class ReleaseRpmHook(RpmsHandler, ColorMixin):

  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-rpm'
    self.eventid = 'release-rpm'
    
    self.interface = interface

    data = {
      'config': [
        '/distro/rpms/release-rpm',    
        '/distro/stores/*/store/gpgkey',
        '/distro/gpgsign',
      ],      
      'variables': [
        'distrosroot',
        'cvars[\'base-vars\'][\'fullname\']',
        'cvars[\'base-vars\'][\'version\']',        
      ],
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
                   interface.getGpgDirectory()),
      'repo'    : ('/distro/rpms/release-rpm/yum-repos/path/text()',
                   interface.getRepoDirectory()),
      'eula'    : ('/distro/rpms/release-rpm/eula/path/text()',
                   interface.getEulaDirectory()),
      'omf'     : ('/distro/rpms/release-rpm/release-notes/omf/path/text()',
                   interface.getOmfDirectory()),
      'html'    : ('/distro/rpms/release-rpm/release-notes/html/path/text()',
                   interface.getHtmlDirectory()),
      'doc'     : ('/distro/rpms/release-rpm/release-notes/doc/path/text()',
                   interface.getDocDirectory()),
      'release' : ('/distro/rpms/release-rpm/release-files/path/text()',
                   interface.getReleaseDirectory()),
      'etc'     : (None,
                   interface.getEtcDirectory()), 
      'eulapy'  : (None,
                   interface.getEulaPyDirectory()),
    }

    RpmsHandler.__init__(self, interface, data, 'release-rpm',
                         '%s-release' \
                         % interface.cvars['base-vars']['product'],
                         summary='%s release files' \
                         % interface.cvars['base-vars']['fullname'],
                         description='%s release files created by '
                         'dimsbuild' \
                         % interface.cvars['base-vars']['fullname'],
                         installinfo=installinfo)
    
    ColorMixin.__init__(self)

  def _generate(self):
    "Create files besides the ones that have been synced."
    for type in self.installinfo.keys():
      function = '_create_%s_files' %type      
      if hasattr(self, function):
        getattr(self, function)()

    self._verify_release_notes()

  def _get_config_files(self):
    rtn = None
    for k,v in self.installinfo.items():
      installpath = v[1]

      if installpath.startswith('/etc'): # is a config file
        dir = join(self.output_location, k)
        if not exists(dir):
          continue
        value = '\n\t'.join([ join(installpath, basename(x)) for x in os.listdir(dir) ])
        if rtn is None: rtn = value
        else          : rtn = '\n\t'.join([rtn.strip(), value])
    return rtn

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
      path = join(dir, 'RELEASE-NOTES-%s.html' %(locale.getdefaultlocale()[0],))

      f = open(path, 'w')      
      f.write(RELEASE_NOTES_HTML %(self.bgcolor, self.textcolor, self.fullname))      
      f.close()
      
      index_html = join(self.output_location, 'html', 'index.html')
      if not exists(index_html):
        os.link(path, index_html)
      
  def _create_repo_files(self):
    reposdir = join(self.output_location, 'repo')
    if not exists(reposdir):
      mkdir(reposdir, parent=True)
      
    if self.config.get('/distro/rpms/release-rpm/yum-repos/publish-repo/include/text()', 'True') \
           in BOOLEANS_TRUE:
      repofile = join(reposdir, '%s.repo' %(self.product,))
      authority = self.config.get('/distro/rpms/release-rpm/publish-repo/authority/text()',
                                  ''.join(['http://', self.interface.getIpAddress()]))
      path = join(self.interface.distrosroot, self.interface.pva, 'os')
      lines = ['[%s]' %(self.product,),
               'name=%s %s - %s' %(self.fullname, self.version, self.arch,),
               'baseurl=%s' %(join(authority, path),)]
      
      if self.config.get('/distro/gpgsign/sign/text()', 'False') in BOOLEANS_TRUE:
        gpgkey = self.config.get('/distro/gpgsign/public/text()')
        lines.extend(['gpgcheck=1', 'gpgkey=%s' %(gpgkey,)])
      else:
        lines.append('gpgcheck=0')
        
      filereader.write(lines, repofile)

    if self.config.get('/distro/rpms/release-rpm/yum-repos/input-repo/include/text()', 'False') \
           in BOOLEANS_TRUE:
      repofile = join(reposdir, 'source.repo')
      rc = YumRepoCreator(repofile, self.config.file, '/distro/stores')
      rc.createRepoFile()

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
    filereader.write(release_string, join(etcdir, '%s-release' %(self.product,)))
    
    # write the issue and issue.net files
    filereader.write(release_string+issue_string, join(etcdir, 'issue'))    
    filereader.write(release_string+issue_string, join(etcdir, 'issue.net'))


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
