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
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS',
    'requires': ['source-vars'],
  },    
]

HOOK_MAPPING = {
  'ReleaseRpmHook': 'release-rpm',
}

API_VERSION = 4.1

#---------- HANDLERS -------------#
class ReleaseRpmHook(RpmsHandler, ColorMixin):

  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'release.release-rpm'
    self.eventid = 'release-rpm'
    
    self.interface = interface

    data = {
      'config': [
        '/distro/main/fullname/text()',
        '/distro/main/version/text()',
        '/distro/rpms/release-rpm',    
        '/distro/stores/*/store/gpgkey',
        '/distro/gpgsign',
      ],      
      'variables': ['distrosroot'],
      'input': [],
      'output': [],
    }

    RpmsHandler.__init__(self, interface, data, 'release-rpm',
                         '%s-release' %(interface.product,),
                         description='%s release files' %(interface.fullname,),
                         long_description='%s release files created by dimsbuild' \
                         %(interface.fullname,))
    
    ColorMixin.__init__(self)

    #  Each key of the installinfo directionary is the name of the directory in
    # release RPM event's working directory and its value tells the program
    # what it should do with those files.
    #
    #  Each value of in the installinfo dictionary should be a string or a 2-tuple.
    # If it is a string, it should be install directory. If it's a 2-tuple, it should
    # be the default install directory and the xpath query to the user-specified
    # install path.
    #
    #  For example, self.installinfo['gpg'] are installed to /etc/pki/rpm-gpg.
    self.installinfo = {
      'gpg'     : ('/distro/stores/*/store/gpgkey/text()', '/etc/pki/rpm-gpg', None),
      'repo'    : ('/distro/rpms/release-rpm/yum-repos/path/text()', '/etc/yum.repos.d', None),
      'eula'    : ('/distro/rpms/release-rpm/eula/path/text()', '/usr/share/eula', None),
      'omf'     : ('/distro/rpms/release-rpm/release-notes/omf/path/text()',
                   '/usr/share/omf/%s-release-notes' %(self.product,),
                   '/distro/rpms/release-rpm/release-notes/omf/@install-path'),
      'html'    : ('/distro/rpms/release-rpm/release-notes/html/path/text()',
                   '/usr/share/doc/HTML',
                   '/distro/rpms/release-rpm/release-notes/html/@install-path'),
      'doc'     : ('/distro/rpms/release-rpm/release-notes/doc/path/text()',
                   '/usr/share/doc/%s-release-notes-%s' %(self.product, self.version,),
                   '/distro/rpms/release-rpm/release-notes/doc/@install-path'),                   
      'release' : ('/distro/rpms/release-rpm/release-files/path/text()',
                   '/usr/share/doc/%s-release-%s' %(self.product, self.version,),
                   None),
      'etc'     : (None, '/etc', None), 
      'eulapy'  : (None, '/usr/share/firstboot/modules', None),
    }

  def setup(self):
    for k,v in self.installinfo.items():
      xquery,_,_ = v
      if xquery is not None:
        self.addInput(self.interface.config.xpath(xquery, []))
    self.expandInput()

  def _copy(self):
    for k,v in self.installinfo.items():
      xquery,_,_ = v
      if xquery is not None:
        for file in self.interface.config.xpath(xquery, []):
          dest = join(self.output_location, k)
          if not exists(dest):
            mkdir(dest, parent=True)
          sync(file, dest)
    
  def _generate(self):
    "Create files besides the ones that have been synced."
    for type in self.installinfo.keys():
      function = '_create_%s_files' %type      
      if hasattr(self, function):
        getattr(self, function)()

    self._verify_release_notes()

  def _create_manifest(self): # done by _get_data_files(), below
    pass

  def _get_data_files(self):
    data = None  
    manifest = ['setup.py', 'setup.cfg']
    for k,v in self.installinfo.items():
      dir = join(self.output_location, k)
      if exists(dir):
        files = [ join(k,x) for x in os.listdir(dir) ]
      else:
        files = []

      if files:        
        manifest.extend(files)
        if v[2] is not None: installpath = self.config.get(v[2], None) or v[1]
        else: installpath = v[1]
        
        datum = '%s : %s' %(installpath, ', '.join(files))
        if data is None:
          data = datum
        else:
          data = '\n\t'.join([data.strip(), datum])
    filereader.write(manifest, join(self.output_location, 'MANIFEST'))
    return data

  def _get_config_files(self):
    rtn = None
    for k,v in self.installinfo.items():
      if v[2] is not None: installpath = self.config.get(v[2], None) or v[1]
      else: installpath = v[1]

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
