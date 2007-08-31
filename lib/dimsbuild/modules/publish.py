import fcntl
import socket
import struct

from dims import filereader
from dims import pps
from dims import shlib

from dims.repocreator import YumRepoCreator

from dimsbuild.constants import *
from dimsbuild.event     import EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface

P = pps.Path

API_VERSION = 4.1

EVENTS = [
  {
    'id': 'repofile',
    'properties': EVENT_TYPE_MDLR,
  },
  {
    'id': 'publish',
    'interface': 'PublishInterface',
    'properties': EVENT_TYPE_MDLR,
    'conditional-requires': ['MAIN', 'ISO'],
    'parent': 'ALL',
  },
]

HOOK_MAPPING = {
  'RepofileHook': 'repofile',
  'PublishHook':  'publish',
}


class PublishInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)

    self.PUBLISH_DIR = \
      P(self.config.get('/distro/publish/local-webroot/text()', '/var/www/html')) / \
        self.config.get('/distro/publish/path-prefix/text()', 'distros') / \
        self.pva


#------ HOOKS ------#
class RepofileHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'publish.repofile'
    
    self.interface = interface
    
    self.repodir = self.interface.METADATA_DIR/'RPMS/rpms-src/release-rpm/etc/yum.repos.d'
    self.repofile    = self.repodir/('%s.repo' % self.interface.product)
    self.srcrepofile = self.repodir/'source.repo'
    
    self.DATA =  {
      'config':    ['/distro/publish'],
      'variables': ['cvars[\'gpg-public-key\']'],
      'output':    [self.repofile]
    }
    self.mdfile = self.interface.METADATA_DIR/'repofile.md'

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
  
  def clean(self):
    self.repofile.rm(force=True)
    self.srcrepofile.rm(force=True)
    self.interface.clean_metadata()
  
  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    # if we're not enabled, clean up and return immediately
    if self.interface.config.get('/distro/publish/repofile/@enabled',
                                 'True') not in BOOLEANS_TRUE:
      self.clean()
      return
    
    self.interface.log(0, "generating yum repo file")
    
    self.repofile.dirname.mkdirs()
    
    authority = self.interface.config.get('/distro/publish/remote-webroot/text()', None) or \
                'http://' + self._getIpAddress()
    path = P(self.interface.config.get('/distro/publish/path-prefix/text()', 'distros')) / \
             self.interface.pva/'os'
    
    lines = [ '[%s]' % self.interface.product,
              'name=%s - %s' % (self.interface.fullname, self.interface.basearch),
              'baseurl=%s/%s' % (authority, path) ]
    
    if self.interface.cvars['gpg-public-key']:
      gpgkey = '%s/%s/%s' % (authority,
                             path,
                             P(self.interface.cvars['gpg-public-key']).basename)
      lines.extend(['gpgcheck=1', 'gpgkey=%s' % gpgkey])
    else:
      lines.append('gpgcheck=0')
    
    filereader.write(lines, self.repofile)
    
    # include source repos too, if requested
    if self.interface.config.get('/distro/publish/repofile/@include-input',
                                 'False') in BOOLEANS_TRUE:
      self.DATA['output'].append(self.srcrepofile)
      
      rc = YumRepoCreator(self.srcrepofile,
                          self.interface.config.file,
                          '/distro/repos')
      rc.createRepoFile()
  
  def apply(self):
    self.interface.write_metadata()
  
  def _getIpAddress(self, ifname='eth0'):
    # TODO - improve this, its not particularly accurate in some cases
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                        0x8915,
                                        struct.pack('256s', ifname[:15]))[20:24])

class PublishHook:
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'publish.publish'
    
    self.interface = interface

    self.DATA =  {
      'variables': ['PUBLISH_DIR'],
      'input':     [],
      'output':    [],
    }
    self.mdfile = self.interface.METADATA_DIR/'publish.md'

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    paths = []
    for dir in ['os', 'iso', 'SRPMS']:
      pdir = self.interface.OUTPUT_DIR/dir
      if pdir.exists():
        paths.append((pdir, self.interface.PUBLISH_DIR))
    if paths:
      o = self.interface.setup_sync(paths=paths)
      self.DATA['output'].extend(o)

  def clean(self):
    self.interface.log(0, "cleaning publish event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
    
  def run(self):
    "Publish the contents of interface.SOFTWARE_STORE to interface.PUBLISH_STORE"
    self.interface.log(0, "publishing output store")
    self.interface.remove_output()
    self.interface.sync_input(copy=True, link=True)
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % self.interface.PUBLISH_DIR)

    self.interface.write_metadata()
