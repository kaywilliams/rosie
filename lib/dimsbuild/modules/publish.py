import fcntl
import socket
import struct

from dims import filereader
from dims import pps
from dims import shlib

from dims.repocreator import YumRepoCreator

from dimsbuild.constants import *
from dimsbuild.event     import Event

P = pps.Path

API_VERSION = 5.0


class RepoFileEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'repo-file',
      conditionally_requires = ['gpgsign-public-key'],
    )
  
    self.repodir = self.METADATA_DIR/'RPMS/rpms-src/release-rpm/etc/yum.repos.d'
    self.repofile    = self.repodir/'%s.repo' % self.product
    self.srcrepofile = self.repodir/'source.repo'
    
    self.DATA =  {
      'config':    ['/distro/publish'],
      'variables': ['cvars[\'gpgsign-public-key\']',
                    'product'],
      'output':    [self.repofile]
    }

  def _setup(self):
    self.setup_diff(self.DATA)
  
  def _clean(self):
    self.repofile.rm(force=True)
    self.srcrepofile.rm(force=True)
    self.clean_metadata()
  
  def _run(self):
    # if we're not enabled, clean up and return immediately
    if self.config.get('/distro/publish/repofile/@enabled',
                       'True') not in BOOLEANS_TRUE:
      self._clean()
      return
    
    self.log(0, "generating yum repo file")
    
    self.repofile.dirname.mkdirs()
    
    authority = self.config.get('/distro/publish/remote-webroot/text()', None) or \
                'http://' + self._getIpAddress()
    path = P(self.config.get('/distro/publish/path-prefix/text()', 'distros')) / \
             self.pva/'os'
    
    lines = [ '[%s]' % self.product,
              'name=%s - %s' % (self.fullname, self.basearch),
              'baseurl=%s/%s' % (authority, path) ]
    
    if self.cvars['gpgsign-public-key']:
      gpgkey = '%s/%s/%s' % (authority,
                             path,
                             P(self.cvars['gpgsign-public-key']).basename)
      lines.extend(['gpgcheck=1', 'gpgkey=%s' % gpgkey])
    else:
      lines.append('gpgcheck=0')
    
    filereader.write(lines, self.repofile)
    
    # include source repos too, if requested
    if self.config.get('/distro/publish/repofile/@include-input',
                       'False') in BOOLEANS_TRUE:
      self.DATA['output'].append(self.srcrepofile)
      
      rc = YumRepoCreator(self.srcrepofile,
                          self.config.file,
                          '/distro/repos')
      rc.createRepoFile()
    
    self.write_metadata()

  def _getIpAddress(self, ifname='eth0'):
    # TODO - improve this, its not particularly accurate in some cases
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                        0x8915,
                                        struct.pack('256s', ifname[:15]))[20:24])

class PublishEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish',
      requires = ['composed-tree'],
      comes_after = ['MAIN', 'ISO'],
    )
    
    self.PUBLISH_DIR = \
      P(self.config.get('/distro/publish/local-webroot/text()', '/var/www/html')) / \
        self.config.get('/distro/publish/path-prefix/text()', 'distros') / \
        self.pva
    
    self.DATA =  {
      'variables': ['PUBLISH_DIR'],
      #'input':     [],
      #'output':    [],
    }
  
  def _setup(self):
    self.setup_diff(self.DATA)
    #for dir in self.cvars['composed-tree'].listdir():
    #  self.setup_sync(self.PUBLISH_DIR, paths=[dir])
  
  def _run(self):
    "Publish the contents of SOFTWARE_STORE to PUBLISH_STORE"
    self.log(0, "publishing output store")
    #self.remove_output()
    self.PUBLISH_DIR.rm(recursive=True, force=True)
    #self.sync_input(copy=True, link=True)
    for dir in self.cvars['composed-tree'].listdir():
      self.copy(dir, self.PUBLISH_DIR, link=True)
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % self.PUBLISH_DIR)
    
    self.write_metadata()

EVENTS = {'ALL': [PublishEvent], 'MAIN': [RepoFileEvent]}
