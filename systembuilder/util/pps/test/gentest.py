import copy

from systembuilder.util import pps

# update individual values in the appropriate section below if neccessary
PATH_DEFAULTS = {
  'root':   '/',
  'sep':    '/',
  'curdir': '.',
  'pardir': '..',
}

PATHS = [
  { # posix paths
    'pathcls':  'PosixPath',
    'pathtype': 'posix',
    'scheme':   'file',
    'netloc':   'localhost',
  },
  { # nt paths
    # nt paths dont pass right now b/c of annoying '\' escape issues
    'pathcls':  'NTPath',
    'pathtype': 'nt',
    'root':     r'c:\\',
    'sep':      r'\\', # doubled for replacement
    'scheme':   'file',
    'netloc':   'localhost',
  },
  #{ # local paths
  #  'pathcls':  'LocalPath',
  #  'pathtype': 'local',
  #  'scheme':   'file',
  #  'netloc':   'localhost',
  #},
  { # http paths
    'pathcls':  'HttpPath',
    'pathtype': 'http',
    'root':     'http://www.ex.com/',
    'scheme':   'http',
    'netloc':   'www.ex.com',
  },
  { # mirror paths
    'pathcls':  'MirrorPath',
    'pathtype': 'mirror',
    'root':     'mirror:/tmp/mirrorlist::/',
    'scheme':   'mirror',
    'netloc':   '/tmp/mirrorlist',
  },
  #{ # ftp paths (not ready yet)
  #  'pathcls':  'FtpPath',
  #  'pathtype': 'ftp',
  #  'root':     'ftp://ftp.ex.com/',
  #  'scheme':   'ftp':
  #  'netloc':   'ftp.ex.com',
  #},
]

for pathinfo in PATHS:
  # prepare replacement
  defaults = copy.copy(PATH_DEFAULTS)
  defaults.update(pathinfo)
  pathinfo = defaults

  pdir = pps.path(pathinfo['pathcls'])
  pdir.mkdirs()

  pathinfo.update({
    'abspath': '%(root)sa%(sep)sb' % pathinfo,
    'abspath-noroot': 'a%(sep)sb' % pathinfo,
    'abspath-basename': 'b' % pathinfo,
    'abspath-dirname': '%(root)sa' % pathinfo,
    'abspath-uri': '%(scheme)s://%(netloc)s%(sep)sa%(sep)sb' % pathinfo,
    'relpath': 'c%(sep)sd' % pathinfo,
    'relpath-noroot': 'c%(sep)sd' % pathinfo,
    'relpath-basename': 'd' % pathinfo,
    'relpath-dirname': 'c' % pathinfo,
    'relpath-uri': 'c%(sep)sd' % pathinfo,
  })

  for template in pdir.getcwd().listdir('*.tpl'):
    (pdir/template.basename.splitext()[0]).write_text(template.read_text() % pathinfo)
