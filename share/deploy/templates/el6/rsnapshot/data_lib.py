
from deploy.util      import pps
import json

ETC_DIR = '/etc'
JSON_EXT = '.json'

CONF_FILE        = 'rsnapshot.conf'
SCRIPT_DIR       = 'rsnapshot.d/scripts'
KNOWN_HOSTS_FILE = 'rsnapshot.d/known_hosts'


class RsnapshotDataWriter:
  def __init__(self, dataroot, deploy_module, rsnapshot_module):
    self.data = {}
    self.file = pps.path('%s/%s/%s%s' % (dataroot, deploy_module, 
                                         rsnapshot_module, JSON_EXT))

  def add_host(self, hostfile):
    host = pps.path(hostfile).read_text().rstrip()
    self.data.setdefault('hosts', []).append(host)

  def add_conf(self, text):
    self.data.setdefault('conf', []).append(text)

  def add_script(self, name, text):
    self.data.setdefault('scripts', {})[name] = text

  def add_user(self, user, pubkey):
    self.data['user'] = pubkey

  def add_restore_root(self, restore_root):
    self.data.setdefault('restore_roots', []).append(restore_root)

  def write_data(self):
    if self.data:
      self.file.dirname.mkdirs(mode=0700)
      self.file.write_text(json.dumps(self.data, sort_keys=True, indent=0))
      self.file.chmod(0700)


class RsnapshotDataComposer:
  def __init__(self, dataroot, deploy_module, composeroot, baseconf):
    data = []
    for file in pps.path('%s/%s' % (dataroot, deploy_module)).findpaths(
                         mindepth=1, maxdepth=1, type=pps.constants.TYPE_FILE,
                         glob='*%s' % JSON_EXT):
      data.append(json.loads(file.read_text()))
    composeroot = pps.path(composeroot)

    for d in [ composeroot, composeroot / SCRIPT_DIR ]:
      d.mkdirs(mode=0700)
      d.chown(0,0)

    # write conf
    txt = baseconf
    includes = []
    for i in [ x.get('conf', []) for x in data ]:
      includes.extend(i)
    txt = txt + '\n'.join(includes).rstrip() + '\n'
    (composeroot / CONF_FILE).write_text(txt)
    
    # write known_hosts
    txt = ''
    hosts = []
    for i in [ x.get('hosts', []) for x in data ]:
      hosts.extend(i)
    txt = txt + '\n'.join(hosts).rstrip() + '\n'
    (composeroot / KNOWN_HOSTS_FILE ).write_text(txt)

    # write rsnapshot.d files
    scripts = {} 
    for i in [ x.get('scripts', {}) for x in data ]:
      scripts.update(i)
    for f,t in scripts.items():
      pps.path(composeroot / SCRIPT_DIR / f).write_text(t)
