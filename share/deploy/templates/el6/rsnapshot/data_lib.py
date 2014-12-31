from deploy.util import pps

INC_FILE = 'include'
KEY_FILE = 'known_hosts'

SCRIPT_INFIX = 'scripts'

ETC_DIR = pps.path('/etc')

CONF_FILE        = 'rsnapshot.conf'
SCRIPT_DIR       = 'rsnapshot.d/%s' % SCRIPT_INFIX
KNOWN_HOSTS_FILE = 'rsnapshot.d/%s' % KEY_FILE


class RsnapshotDataWriter:
  def __init__(self, dataroot):
    self.dataroot = pps.path(dataroot)

    self.incfile = dataroot / INC_FILE
    self.keyfile = dataroot / KEY_FILE
    self.scriptdir = dataroot / SCRIPT_INFIX


    self.SCRIPT_DIR = ETC_DIR / SCRIPT_DIR
    self.KNOWN_HOSTS_FILE = ETC_DIR / KNOWN_HOSTS_FILE

    # setup
    self.dataroot.rm(recursive=True, force=True)
    for d in [ self.dataroot, self.scriptdir ]:
      d.mkdirs(mode=0700)
      d.chown(0,0)

  def write_key(self, keyfile):
    keyfile = pps.path(keyfile)
    self.keyfile.write_text(keyfile.read_text().rstrip() + '\n', append=True)

  def write_conf(self, text):
    self.incfile.write_text(text, append=True)

  def write_script(self, name, text):
    (self.scriptdir / name).write_text(text)


class RsnapshotDataComposer:
  def __init__(self, userroot, composeroot, baseconf):
    userroot = pps.path(userroot)
    composeroot = pps.path(composeroot)

    for d in [ composeroot, composeroot / SCRIPT_DIR ]:
      d.mkdirs(mode=0700)
      d.chown(0,0)

    # write conf
    txt = baseconf
    for f in userroot.findpaths(INC_FILE, mindepth=2, maxdepth=2):
      txt = txt + '\n' + f.read_text()
    (composeroot / CONF_FILE).write_text(txt)
    
    # write known_hosts
    txt = ''
    for f in userroot.findpaths(KEY_FILE, mindepth=2, maxdepth=2):
      txt = txt + f.read_text()
    (composeroot / KNOWN_HOSTS_FILE ).write_text(txt)

    # assemble rsnapshot.d files 
    for d in userroot.findpaths(SCRIPT_INFIX, mindepth=2, maxdepth=2,
                                              type=pps.constants.TYPE_DIR):
        for i in d.listdir():
          i.cp(composeroot / SCRIPT_DIR, recursive=True)
