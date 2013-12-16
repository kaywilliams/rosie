"Default repository definitions"

from deploy.util.repo import ReposFromString

__all__ = ['getDefaultRepos', 'getDefaultPackageRepos',
           'getDefaultSourceRepos', 'getDefaultInstallerRepos',
           'getDefaultRepoById', 'NoSuchRepoError']

DISTRO_FEDORA = 'fedora'
DISTRO_REDHAT = 'rhel'
DISTRO_CENTOS = 'centos'

TYPE_INSTALLER = 'installer'
TYPE_PACKAGES  = 'packages'
TYPE_SOURCE    = 'source'

TYPE_ALL = [TYPE_PACKAGES, TYPE_SOURCE, TYPE_INSTALLER]

def getDefaultRepos(type, os, version, **kwargs):
  return _makeRepos(os, version, type, **kwargs)
def getDefaultPackageRepos(os, version, **kwargs):
  return _makeRepos(os, version, TYPE_PACKAGES, **kwargs)
def getDefaultSourceRepos(os, version, **kwargs):
  return _makeRepos(os, version, TYPE_SOURCE, **kwargs)
def getDefaultInstallerRepos(os, version, **kwargs):
  return _makeRepos(os, version, TYPE_INSTALLER, **kwargs)
def getDefaultRepoById(id, os, version, **kwargs):
  # this is kind of a kludgy way to do it...
  for type in TYPE_ALL:
    repos = getDefaultRepos(type, os, version, **kwargs)
    if repos and id in repos:
      return repos[id]
  raise NoSuchRepoError("No such repo id '%s'" % id)

from deploy.util.repo.repo import BaseRepo, YumRepo # avoid circular ref

def _makeRepos(os, version, type,
               cls=YumRepo, arch=None, include_baseurl=False,
               baseurl=None, mirrorlist=None):

  # set up replacement vars for repo input string
  baseurl    = baseurl    or DEFAULTS[os]['baseurl']
  mirrorlist = mirrorlist or DEFAULTS[os]['mirrorlist']

  gpgkey = _getitem_(GPGKEYS[os] or '', version) % dict(baseurl=baseurl)

  map = dict(baseurl=baseurl, mirrorlist=mirrorlist, gpgkey=gpgkey)

  src = _getitem_(REPO_DATA[type][os], version)

  if src:
    repos = ReposFromString(src % map, cls=cls)

    for repo in repos.values():
      # automatically discard baseurl if repo has a mirrorlist and we're
      # not explicitly asked to keep it
      if repo.mirrorlist and not include_baseurl:
        del repo['baseurl']

    # set up replacement vars for repo
    vars = {'$releasever': version}
    if arch: vars['$basearch'] = arch
    for repo in repos.values():
      repo.vars = vars

    return repos
  else:
    return None

def _getitem_(self, version):
  if isinstance(self, dict):
    for key in self.keys():
      if version in key:
        self = self[key]
  if isinstance(self, dict):
    raise KeyError, version
  return self


DEFAULTS = {
  DISTRO_FEDORA: {
    # path to a fedora mirrorlist script; it will be passed path=... as
    # its query argument
    'mirrorlist': 'http://mirrors.fedoraproject.org/mirrorlist',
    # path to a location at the root of a fedora mirror; beneath it is
    # typically 'core', 'releases', etc
    'baseurl':    'http://dl.fedoraproject.org/pub/fedora/linux',
  },
  DISTRO_REDHAT: {
    # redhat has no publicly-available mirrorlist
    'mirrorlist': '',
    # baseurl is a path to a location at the root of a redhat mirror;
    # beneath it is typically 'enterprise'
    'baseurl':    'http://ftp.redhat.com/pub/redhat/linux',
  },
  DISTRO_CENTOS: {
    # path to a centos mirrorlist script; it will be passed arch=...,
    # version=..., and repo=... as query arguments
    'mirrorlist': 'http://mirrorlist.centos.org/',
    # path to a location at the root of a centos mirror; beneath it is
    # typically '4', '5', etc
    'baseurl':    'http://mirror.centos.org/centos',
  },
}
DEFAULTS['%s.newkey' % DISTRO_FEDORA] = DEFAULTS[DISTRO_FEDORA]

#============ FEDORA ============#

_FEDORA_GPGKEYS = ' '.join(['%(gpgkeyroot)s',
                            '%(gpgkeyroot)s-beta',
                            '%(gpgkeyroot)s-fedora',
                            '%(gpgkeyroot)s-fedora-rawhide',
                            '%(gpgkeyroot)s-fedora-test',
                            '%(gpgkeyroot)s-rawhide'])
FEDORA_GPGKEYS_OLD = _FEDORA_GPGKEYS % \
  dict(gpgkeyroot='%(baseurl)s/core/$releasever/$basearch/os/RPM-GPG-KEY')

# fedora 1-6
FEDORA_PACKAGES_OLD = \
"""[base]
name       = base
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/core/$releasever/$basearch/os/
baseurl    = %(baseurl)s/core/$releasever/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything]
name       = everything
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/extras/$releasever/$basearch/
baseurl    = %(baseurl)s/extras/$releasever/$basearch/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[updates]
name       = updates
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/core/updates/$releasever/$basearch/
baseurl    = %(baseurl)s/core/updates/$releasever/$basearch/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

FEDORA_SOURCE_OLD = \
"""[base-source]
name       = base-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/core/$releasever/source/SRPMS/
baseurl    = %(baseurl)s/core/$releasever/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything-source]
name       = everything-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/extras/$releasever/source/SRPMS/
baseurl    = %(baseurl)s/extras/$releasever/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[updates-source]
name       = updates-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/core/updates/$releasever/SRPMS/
baseurl    = %(baseurl)s/core/updates/$releasever/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

FEDORA_INSTALLER_OLD = \
"""[installer]
name       = installer
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/core/$releasever/$basearch/os/
baseurl    = %(baseurl)s/core/$releasever/$basearch/os/
"""

# fedora 7-9
FEDORA_GPGKEYS = _FEDORA_GPGKEYS % \
  dict(gpgkeyroot='%(baseurl)s/releases/$releasever/Fedora/$basearch/os/RPM-GPG-KEY')

FEDORA_PACKAGES = \
"""[base]
name       = base
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Fedora/$basearch/os/
baseurl    = %(baseurl)s/releases/$releasever/Fedora/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything]
name       = everything
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Everything/$basearch/os/
baseurl    = %(baseurl)s/releases/$releasever/Everything/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[updates]
name       = updates
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/updates/$releasever/$basearch/
baseurl    = %(baseurl)s/updates/$releasever/$basearch/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

FEDORA_SOURCE = \
"""[base-source]
name       = base-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Fedora/source/SRPMS/
baseurl    = %(baseurl)s/releases/$releasever/Fedora/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything-source]
name       = everything-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Everything/source/SRPMS/
baseurl    = %(baseurl)s/releases/$releasever/Everything/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[updates-source]
name       = updates-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/updates/$releasever/SRPMS/
baseurl    = %(baseurl)s/updates/$releasever/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

FEDORA_INSTALLER = \
"""[installer]
name       = installer
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Fedora/$basearch/os/
baseurl    = %(baseurl)s/releases/$releasever/Fedora/$basearch/os/
"""


# fedora newkey - I think this is temporary
FEDORA_PACKAGES_NEWKEY = \
"""[base]
name       = base
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Fedora/$basearch/os/
baseurl    = %(baseurl)s/releases/$releasever/Fedora/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything]
name       = everything
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Everything/$basearch/os/
baseurl    = %(baseurl)s/releases/$releasever/Everything/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[updates]
name       = updates
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/updates/$releasever/$basearch.newkey/
baseurl    = %(baseurl)s/updates/$releasever/$basearch.newkey/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

FEDORA_SOURCE_NEWKEY = \
"""[base-source]
name       = base-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Fedora/source/SRPMS/
baseurl    = %(baseurl)s/releases/$releasever/Fedora/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything-source]
name       = everything-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/$releasever/Everything/source/SRPMS/
baseurl    = %(baseurl)s/releases/$releasever/Everything/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[updates-source]
name       = updates-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/updates/$releasever/SRPMS.newkey/
baseurl    = %(baseurl)s/updates/$releasever/SRPMS.newkey/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""


# fedora beta
FEDORA_GPGKEYS_BETA = ' '.join(['%(gpgkeyroot)s',
                                '%(gpgkeyroot)s-primary',
                                '%(gpgkeyroot)s-test-primary']) % \
  dict(gpgkeyroot='%(baseurl)s/releases/test/$releasever/Fedora/$basearch/os/RPM-GPG-KEY-fedora')

FEDORA_PACKAGES_BETA = \
"""[base]
name       = base
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/test/$releasever/Fedora/$basearch/os/
baseurl    = %(baseurl)s/releases/test/$releasever/Fedora/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything]
enabled    = no

[updates]
enabled    = no
"""

FEDORA_SOURCE_BETA = \
"""[base-source]
name       = base-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/test/$releasever/Fedora/source/SRPMS/
baseurl    = %(baseurl)s/releases/test/$releasever/Fedora/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything-source]
enabled    = no

[updates-source]
enabled    = no
"""

FEDORA_INSTALLER_BETA = \
"""[installer]
name       = installer
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/releases/test/$releasever/Fedora/$basearch/os/
baseurl    = %(baseurl)s/releases/test/$releasever/Fedora/$basearch/os/
"""

# fedora devel
FEDORA_GPGKEYS_DEVEL = ' '.join(['%(gpgkeyroot)s',
                                 '%(gpgkeyroot)s-10-primary',
                                 '%(gpgkeyroot)s-primary',
                                 '%(gpgkeyroot)s-test-10-primary',
                                 '%(gpgkeyroot)s-test-primary']) % \
  dict(gpgkeyroot='%(baseurl)s/development/$basearch/os/RPM-GPG-KEY-fedora')

FEDORA_PACKAGES_DEVEL = \
"""[base]
name       = base
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/development/$basearch/os/
baseurl    = %(baseurl)s/development/$basearch/os/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything]
enabled    = no

[updates]
enabled    = no
"""

FEDORA_SOURCE_DEVEL = \
"""[base-source]
name       = base-source
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/development/source/SRPMS/
baseurl    = %(baseurl)s/development/source/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything-source]
enabled    = no

[updates-source]
enabled    = no
"""

FEDORA_INSTALLER_DEVEL = \
"""[installer]
name       = installer
mirrorlist = %(mirrorlist)s?path=pub/fedora/linux/development/$basearch/os/
baseurl    = %(baseurl)s/development/$basearch/os/
"""


#============ CENTOS ============#
CENTOS_GPGKEYS = '%(baseurl)s/$releasever/os/$basearch/RPM-GPG-KEY-CentOS-$releasever'

CENTOS_PACKAGES = \
"""[base]
name       = base
mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=os
baseurl    = %(baseurl)s/$releasever/os/$basearch/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything]
name       = everything
#mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=extras
baseurl    = http://download.fedora.redhat.com/pub/epel/$releasever/$basearch/
gpgkey     = http://download.fedora.redhat.com/pub/epel/RPM-GPG-KEY-EPEL
gpgcheck   = yes

[updates]
name       = updates
mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=updates
baseurl    = %(baseurl)s/$releasever/updates/$basearch/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

CENTOS_SOURCE = \
"""[base-source]
name       = base-source
#mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=???
baseurl    = %(baseurl)s/$releasever/os/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes

[everything-source]
name       = everything-source
#mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=???
baseurl    = http://download.fedora.redhat.com/pub/epel/$releasever/SRPMS/
gpgkey     = http://download.fedora.redhat.com/pub/epel/RPM-GPG-KEY-EPEL
gpgcheck   = yes

[updates-source]
name       = updates-source
#mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=???
baseurl    = %(baseurl)s/$releasever/updates/SRPMS/
gpgkey     = %(gpgkey)s
gpgcheck   = yes
"""

CENTOS_INSTALLER = \
"""[installer]
name       = installer
mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=os
baseurl    = %(baseurl)s/$releasever/os/$basearch/
"""


#============ REDHAT ============#
REDHAT_GPGKEYS  = None
REDHAT_PACKAGES = \
"""[base]
name       = base
baseurl    = %(baseurl)s/enterprise/$releaseverServer/en/os/$basearch/
gpgkey     = %(baseurl)s/enterprise/$releaseverServer/en/os/$basearch/RPM-GPG-KEY-redhat-release
gpgcheck   = yes

[everything]
name       = everything
#mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=extras
baseurl    = http://download.fedora.redhat.com/pub/epel/$releasever/$basearch/
gpgkey     = http://download.fedora.redhat.com/pub/epel/RPM-GPG-KEY-EPEL
gpgcheck   = yes

[updates]
name       = updates
baseurl    = rhn:///rhel-$basearch-server-5/
systemid   = /etc/sysconfig/rhn/systemid-$releaseverServer-$basearch
gpgkey     = %(baseurl)s/enterprise/$releaseverServer/en/os/$basearch/RPM-GPG-KEY-redhat-release
gpgcheck   = yes
"""
REDHAT_SOURCE = \
"""[base-source]
name       = base-source
#mirrorlist = %(mirrorlist)s/enterprise/$releaseverServer/en/os/SRPMS/
baseurl    = %(baseurl)s/enterprise/$releaseverServer/en/os/SRPMS/
#gpgkey     = %(gpgkey)s
gpgcheck   = no

[everything-source]
name       = everything-source
#mirrorlist = %(mirrorlist)s?release=$releasever&arch=$basearch&repo=???
baseurl    = http://download.fedora.redhat.com/pub/epel/$releasever/SRPMS/
gpgkey     = http://download.fedora.redhat.com/pub/epel/RPM-GPG-KEY-EPEL
gpgcheck   = yes
"""
REDHAT_INSTALLER = None

REPO_DATA = {
  TYPE_PACKAGES: {
    DISTRO_FEDORA: {
      ('1','2','3','4','5','6'):
        FEDORA_PACKAGES_OLD,
      ('7', '8', '9', '19'):
        FEDORA_PACKAGES,
      ('10-Beta'):
        FEDORA_PACKAGES_BETA,
      ('devel'):
        FEDORA_PACKAGES_DEVEL,
    },
    '%s.newkey' % DISTRO_FEDORA: {
      ('8', '9', '19'):
        FEDORA_PACKAGES_NEWKEY,
    },
    DISTRO_REDHAT: REDHAT_PACKAGES,
    DISTRO_CENTOS: CENTOS_PACKAGES,
  },
  TYPE_SOURCE: {
    DISTRO_FEDORA: {
      ('1','2','3','4','5','6'):
        FEDORA_SOURCE_OLD,
      ('7', '8', '9', '19'):
        FEDORA_SOURCE,
      ('10-Beta'):
        FEDORA_SOURCE_BETA,
      ('devel'):
        FEDORA_SOURCE_DEVEL,
    },
    '%s.newkey' % DISTRO_FEDORA: {
      ('8', '9', '19'):
        FEDORA_SOURCE_NEWKEY,
    },
    DISTRO_REDHAT: REDHAT_SOURCE,
    DISTRO_CENTOS: CENTOS_SOURCE,
  },
  TYPE_INSTALLER: {
    DISTRO_FEDORA: {
      ('1','2','3','4','5','6'):
        FEDORA_INSTALLER_OLD,
      ('7','8','9', '19'):
        FEDORA_INSTALLER,
      ('10-Beta'):
        FEDORA_INSTALLER_BETA,
      ('devel'):
        FEDORA_INSTALLER_DEVEL,
    },
    DISTRO_REDHAT: REDHAT_INSTALLER,
    DISTRO_CENTOS: CENTOS_INSTALLER,
  },
}

GPGKEYS = {
  DISTRO_FEDORA: {
    ('1','2','3','4','5','6'):
      FEDORA_GPGKEYS_OLD,
    ('7','8','9', '19'):
      FEDORA_GPGKEYS,
    ('10-Beta'):
      FEDORA_GPGKEYS_BETA,
    ('devel'):
      FEDORA_GPGKEYS_DEVEL,
  },
  DISTRO_REDHAT: REDHAT_GPGKEYS,
  DISTRO_CENTOS: CENTOS_GPGKEYS,
}
GPGKEYS['%s.newkey' % DISTRO_FEDORA] = GPGKEYS[DISTRO_FEDORA]

class NoSuchRepoError(KeyError): pass
