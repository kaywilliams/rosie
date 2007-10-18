import fcntl
import socket
import struct

from dims import pps
from dims import shlib

from dimsbuild.constants import *
from dimsbuild.event     import Event
from dimsbuild.logging   import L0

P = pps.Path

API_VERSION = 5.0


class PublishSetupEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish-setup',
      provides = ['publish-content', 'publish-path', 'web-path', ],
      conditionally_requires = ['gpgsign-public-key'],
    )

    self.repofile = self.mddir/'%s.repo' % self.product

    self.DATA = {
      'variables': ['cvars[\'base-vars\']', 'cvars[\'gpgsign-public-key\']'],
      'config': ['.'],
      'output': [self.repofile]
    }

  def setup(self):
    self.diff.setup(self.DATA)

    prefix = \
      P(self.config.get('path-prefix/text()', 'distros')) / \
        self.pva
    web_path = \
      self.config.get('remote-webroot/text()', None) or \
        P('http://' +  self._get_host()) / prefix
    self.web_path = P(web_path)
    self.publish_path = \
      P(self.config.get('local-webroot/text()', '/var/www/html')) / \
        prefix

  def apply(self):
    self.cvars['publish-content'] = set()
    self.cvars['publish-path'] = self.publish_path
    self.cvars['web-path'] = self.web_path

    self.diff.write_metadata()

  def _get_host(self, ifname='eth0'):
    if self.config.get('remote-webroot/@use-hostname', 'False') in BOOLEANS_TRUE:
      return socket.gethostname()
    else:
      # TODO - improve this, its not particularly accurate in some cases
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      return socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                          0x8915,
                                          struct.pack('256s', ifname[:15]))[20:24])


class PublishEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'publish',
      requires = ['publish-path', 'publish-content'],
    )

    self.DATA =  {
      'variables': ['cvars[\'publish-path\']',
                    'cvars[\'publish-content\']'],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)
    for dir in self.cvars['publish-content']:
      self.io.setup_sync(self.cvars['publish-path'], paths=[dir])

    self._backup_relpath = self.files_callback.relpath
    self.files_callback.relpath = self.cvars['publish-path']

  def run(self):
    "Publish the contents of SOFTWARE_STORE to PUBLISH_STORE"
    self.log(0, L0("publishing output store"))
    self.cvars['publish-path'].rm(recursive=True, force=True)
    self.io.sync_input(copy=True, link=True)
    shlib.execute('chcon -R root:object_r:httpd_sys_content_t %s' \
                   % self.cvars['publish-path'])

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self.files_callback.relpath = self._backup_relpath
    del(self._backup_relpath)

EVENTS = {'ALL': [PublishEvent], 'setup':[PublishSetupEvent],}
