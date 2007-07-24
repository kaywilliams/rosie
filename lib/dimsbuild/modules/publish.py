import fcntl
import os
import socket
import struct

from os.path import join, exists

from dims import filereader
from dims import osutils
from dims import shlib
from dims import sortlib
from dims import sync

from dims.repocreator import YumRepoCreator

from dimsbuild.constants import *
from dimsbuild.event     import EVENT_TYPE_MDLR
from dimsbuild.interface import EventInterface, DiffMixin

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'repofile',
    'properties': EVENT_TYPE_MDLR,
  },
  {
    'id': 'publish',
    'interface': 'PublishInterface',
    'properties': EVENT_TYPE_MDLR,
    'conditional-requires': ['MAIN', 'iso'],
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
      join(self.config.get('/distro/publish/local-webroot/text()', '/var/www/html'),
           self.config.get('/distro/publish/path-prefix/text()', 'distros'),
           self.pva)


#------ HOOKS ------#
class RepofileHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'publish.repofile'
    
    self.interface = interface
    
    self.repodir = join(self.interface.METADATA_DIR,
                        'rpms-src/release-rpm', # this is the fragile part
                        'etc/yum.repos.d')
    self.repofile    = join(self.repodir, '%s.repo' % self.interface.product)
    self.srcrepofile = join(self.repodir, 'source.repo')
    
    self.DATA =  {
      'config':    ['/distro/publish'],
      'variables': ['interface.cvars[\'gpg-public-key\']'],
      'output':    [self.repofile]
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'repofile.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def force(self):
    osutils.rm(self.repofile, force=True)
    osutils.rm(self.srcrepofile, force=True)
    self.clean_metadata()
  
  def check(self):
    if not self.interface.isSkipped('publish') and \
       self.interface.config.get('/distro/publish/repofile/@enabled',
                                 'True') in BOOLEANS_TRUE and \
       self.test_diffs():
      self.force()
      return True
    else:
      return False
  
  def run(self):
    self.interface.log(0, "generating yum repo file")
        
    osutils.mkdir(osutils.dirname(self.repofile), parent=True)
    
    authority = self.interface.config.get('/distro/publish/remote-webroot/text()', None) or \
                'http://' + self._getIpAddress()
    path = join(self.interface.config.get('/distro/publish/path-prefix/text()', 'distros'),
                self.interface.pva, 'os')
    
    lines = [ '[%s]' % self.interface.product,
              'name=%s - %s' % (self.interface.fullname, self.interface.basearch),
              'baseurl=%s' % join(authority, path) ]
    
    if self.interface.cvars['gpg-public-key']:
      gpgkey = join(authority,
                    path,
                    osutils.basename(
                      self.interface.cvars['gpg-public-key']
                    ))
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
    self.write_metadata()
  
  def _getIpAddress(self, ifname='eth0'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                        0x8915,
                                        struct.pack('256s', ifname[:15]))[20:24])

class PublishHook(DiffMixin):
  def __init__(self, interface):
    self.VERSION = 1
    self.ID = 'publish.publish'
    
    self.interface = interface

    self.DATA =  {
      'variables': ['interface.PUBLISH_DIR'],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'publish.md')
    
    DiffMixin.__init__(self, self.mdfile, self.DATA)
  
  def force(self):
    osutils.rm(self.interface.PUBLISH_DIR, recursive=True, force=True)
    self.clean_metadata()

  def run(self):
    "Publish the contents of interface.SOFTWARE_STORE to interface.PUBLISH_STORE"
    self.interface.log(0, "publishing output store")

    # Cleanup - remove old publish_dir folders
    if self.test_diffs():

      try:
        olddir = self.handlers['variables'].vars['interface.PUBLISH_DIR']
        oldparent = os.path.dirname(olddir)

        self.interface.log(2, "removing directory '%s'" % olddir)
        osutils.rm(olddir, recursive=True, force=True)

        if not os.listdir(oldparent):
          self.interface.log(2, "removing directory '%s'" % oldparent)        
          osutils.rm(oldparent, force=True)

      except KeyError:
        pass

    if not exists(self.interface.OUTPUT_DIR): return
    
    # sync to output folder
    if not exists(self.interface.PUBLISH_DIR):
      self.interface.log(2, "making directory '%s'" % self.interface.PUBLISH_DIR)
      osutils.mkdir(self.interface.PUBLISH_DIR, parent=True)
    
    for d in ['os', 'iso', 'SRPMS']: # each folder is technically optional
      src = join(self.interface.OUTPUT_DIR, d)
      if not exists(src): # clean up any existing folders if not present in input
        osutils.rm(join(self.interface.PUBLISH_DIR, d), recursive=True, force=True)
        continue
      sync.sync(src, self.interface.PUBLISH_DIR, link=True, strict=True)
    
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' % self.interface.PUBLISH_DIR)

    self.write_metadata()
