
from deploy.util      import pps
import json

ETC_DIR = '/etc'
JSON_EXT = '.json'

CONF_FILE        = 'rsnapshot.conf'
SCRIPT_DIR       = 'rsnapshot.d/scripts'
KNOWN_HOSTS_FILE = 'rsnapshot.d/known_hosts'


class RsnapshotDataWriter:
  def __init__(self, dataroot, module):
    self.data = {}
    self.file = pps.path('%s/%s%s' % (dataroot, module, JSON_EXT))

  def add_host(self, hostfile):
    host = pps.path(hostfile).read_text().rstrip()
    self.data.setdefault('hosts', []).append(host)

  def add_conf(self, text):
    self.data.setdefault('conf', []).append(text)

  def add_script(self, name, text):
    self.data.setdefault('scripts', {})[name] = text

  def add_authkey(self, keyfile):
    self.data.setdefault('authkeys', []).append(pps.path(keyfile).read_text())

  def write_data(self):
    if self.data:
      self.file.dirname.mkdirs(mode=0700)
      self.file.write_text(json.dumps(self.data, sort_keys=True, indent=0))
      self.file.chmod(0700)
