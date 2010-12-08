#
# Copyright (c) 2010
# Rendition Software, Inc. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
"""
pkgorder.py

Order RPMS so that they can be sequentially installed

This version requires YUM version 3.0 to function.
"""

import os
import rpmUtils
import re
import signal
import sys
import yum

import logging

from yum.transactioninfo import SortableTransactionData
from yum.constants       import *

from systemstudio.util import pps

# groups yanked right out of pkgorder; I made up the names
ORDER_GROUPS = [
  ('base',
    [ 'core', 'base', 'text-internet' ]),
  ('desktop environment',
    [ 'base-x', 'dial-up', 'graphical-internet', 'editors', 'graphics',
      'gnome-desktop', 'sound-and-video', 'printing' ]),
  ('office and productivity',
    [ 'office', 'engineering-and-scientific', 'authoring-and-publishing',
      'games' ]),
  ('server software',
    [ 'web-server', 'ftp-server', 'sql-server', 'mysql', 'server-cfg',
      'dns-server', 'smb-server', 'admin-tools' ]),
  ('development tools',
    [ 'kde-desktop', 'development-tools', 'development-libs',
      'gnome-software-development', 'eclipse', 'x-software-development',
      'java-development', 'kde-software-development', 'mail-server',
      'legacy-network-server' ]),
  ('miscellaneous',
    [ 'news-server', 'legacy-software-development' ]),
]

NEVRA_REGEX = re.compile(
  r'^(?P<name>.+)-'
  r'(?:(?P<epoch>[^\:]+)\:)?'
  r'(?P<version>[^\-]+)-'
  r'(?P<release>[^\-]+)\.'
  r'(?P<arch>[^\.]+)\.'
  r'[Rr][Pp][Mm]$'
)

# set up logger
logger  = logging.getLogger('anaconda')
handler = logging.StreamHandler()
handler.setLevel(logging.ERROR)
logger.addHandler(handler)


class Solver(yum.YumBase):
  def __init__(self, config='/etc/yum.conf', root='/tmp/depsolve', arch=None):
    yum.YumBase.__init__(self)
    self.config = config
    self.root = root
    self.arch = arch

    self.deps = {}
    self.path = []
    self.loops = []

  def __del__(self):
    pass

  def setup(self):
    self.doConfigSetup(fn=str(self.config), root=str(self.root), init_plugins=False)
    self.doRpmDBSetup()
    self.conf.cache = 0
    self.doRepoSetup()
    self.doSackSetup(archlist=rpmUtils.arch.getArchList(self.arch))
    self.doTsSetup()
    self.doGroupSetup()
    self.repos.populateSack('enabled', 'filelists') # this could be a problem, but is OK for now

    # Rpm sets its own signal handlers, which caused a bug in socket
    # timeouts to eat Ctl-C's, turning them into EWOULDBLOCK, which
    # gets returned as "... (11, ...".  Note that the underlying
    # socket is a blocking socket, so EWOULDBLOCK is not correct.
    # With the bug fixed, they become EINTR, which isn't so specific,
    # as it could be any signal, but normally only Ctl-C is expected.
    # The signal.signal() below should make this code moot.

    # rpm steals python's SIGINT signal. Steal it back. Should be
    # safe, as yum is careful to close the rpm database on exit.
    signal.signal(signal.SIGINT, signal.default_int_handler)

  def doFileLogSetup(self, *args, **kwargs): pass
  def doLoggingSetup(self, *args, **kwargs): pass
  def getDownloadPkgs(self, *args, **kwargs): pass

  def _provideToPkg(self, req):
    best = None
    (r, f, v) = req

    satisfiers = []
    for po in self.whatProvides(r, f, v):
      if self.tsInfo.getMembers(po.pkgtup):
        self.deps[req] = po
        return po
      if po not in satisfiers:
        satisfiers.append(po)

    if satisfiers:
      best = self.bestPackagesFromList(satisfiers, arch=self.arch)[0]
      self.deps[req] = best
      return best
    return None

  def resolveDeps(self):
    if self.dsCallback: self.dsCallback.start()
    unresolved = self.tsInfo.getMembers()
    while len(unresolved) > 0:
      if self.dsCallback: self.dsCallback.tscheck(len(unresolved))
      unresolved = self.tsCheck(unresolved)
      if self.dsCallback: self.dsCallback.restartLoop()
    self.deps = {}
    self.loops = []
    self.path = []
    return (2, ['Success - deps resolved'])

  def tsCheck(self, tocheck):
    unresolved = []

    for txmbr in tocheck:
      if txmbr.name == "redhat-lsb" and len(tocheck) > 2: # FIXME: this speeds things up a lot
        unresolved.append(txmbr)
        continue
      if self.dsCallback: self.dsCallback.pkgAdded()
      if txmbr.output_state not in TS_INSTALL_STATES:
        continue
      reqs = txmbr.po.returnPrco('requires')
      provs = txmbr.po.returnPrco('provides')

      for req in reqs:
        if req[0].startswith('rpmlib(') or req[0].startswith('config('):
          continue
        if req in provs:
          continue
        dep = self.deps.get(req, None)
        if dep is None:
          dep = self._provideToPkg(req)
          if dep is None:
            continue

        # Skip file-based requires on self, etc
        if txmbr.name == dep.name:
          continue

        if (dep.name, txmbr.name) in WHITE_TUP:
          continue
        if self.tsInfo.exists(dep.pkgtup):
          pkgs = self.tsInfo.getMembers(pkgtup=dep.pkgtup)
          member = self.bestPackagesFromList(pkgs, arch=self.arch)[0]
        else:
          member = self.tsInfo.addInstall(dep)
          unresolved.append(member)

        # Add relationship
        found = False
        for dependspo in txmbr.depends_on:
          if member.po == dependspo:
            found = True
            break
        if not found:
          txmbr.setAsDep(member.po)

    return unresolved

  def teardown(self):
    "clean up for garbage collection"
    self.close()
    self.closeRpmDB()
    self.doUnlock()

    self._conf = None
    self._tsInfo = None
    self._rpmdb = None
    self._up = None
    self._comps = None
    self._pkgSack = None
    self._repos = None

  def _transactionDataFactory(self):
    return SortableTransactionData()

class PackageOrderer(Solver):
  def __init__(self, config='/etc/yum.conf', root='/tmp/pkgorder', arch=None):
    Solver.__init__(self, config=config, root=root, arch=arch)
    self.processed = {}
    self.ordered_pkgtups = []

  def order(self, exclude=[]):
    if self.dsCallback: self.dsCallback.grptotal = len(ORDER_GROUPS)

    self.conf.exclude.extend(exclude)

    for pkg in self.pkgSack.searchNevra(name='kernel'):
      self.ordered_pkgtups.append(pkg.pkgtup)
    for desc, groups in ORDER_GROUPS:
      if self.dsCallback: self.dsCallback.groupAdded(desc)
      self.addGroups(groups)

    # everything else not already handled
    for po in self.pkgSack.returnPackages():
      if po.name.find('kernel') == -1:
        self.tsInfo.addInstall(po)

    self.processTransaction()

    return self.ordered_pkgtups

  def addGroups(self, groups):
    self.initActionTs()
    map(self.selectGroup, filter(lambda x: self.comps.has_group(x), groups))
    self.resolveDeps()
    self.processTransaction()

  def processTransaction(self):
    for pkgtup in self.tsInfo.sort():
      po = self.tsInfo.pkgdict[pkgtup][0].po
      fname = po.returnSimple('relativepath')
      if self.processed.has_key(fname): continue
      self.processed[fname] = True
      self.ordered_pkgtups.append(pkgtup)


#------ HELPER FUNCTIONS ------#
def parse_pkgorder(file):
  """Parses a pkgorder file as output by python's pkgorder script into a list
  of pkgtups.  Note: since filenames do not normally contain epoch information,
  the pkgtups generated by this function will usually contain None in their
  epoch field."""
  pkgtups = []
  pkgs = pps.path(file).read_lines()
  for pkg in pkgs:
    if pkg.startswith('warning') or pkg.startswith('#'): continue
    m = NEVRA_REGEX.match(pkg).groupdict()
    pkgtup = (m['name'], m['arch'], m['epoch'], m['version'], m['release'])
    pkgtups.append(pkgtup)
  return pkgtups

def write_pkgorder(file, pkgtups):
  "Writes a list of pkgtups to a file"
  files = []
  for p in pkgtups:
    if p[2] is not None: epoch = p[2] + ':'
    else: epoch = ''
    files.append('%s-%s%s-%s.%s.rpm' % (p[0], epoch, p[3], p[4], p[1]))
  pps.path(file).write_lines(files)

def order(exclude=[], arch=None, config='/etc/yum.conf', root=None, callback=None):
  if not root:
    tmppath = pps.path('/tmp/pkgorder-%d' % os.getpid())
    tmppath.mkdirs()
  else:
    tmppath = pps.path(root)
  ds = PackageOrderer(config=config, arch=arch, root=tmppath)
  ds.setup()
  ds.dsCallback = callback
  order = ds.order(exclude=exclude)
  ds.teardown()
  if not root:
    tmppath.rm(recursive=True, force=True)
  return order


#------ CONSTANTS -----#
WHITEOUT='''
pango-gtkbeta-devel>pango-gtkbeta
XFree86>Mesa
xorg-x11>Mesa
compat-glibc>db2
compat-glibc>db1
pam>initscripts
initscripts>sysklogd
arts>kdelibs-sound
libgnomeprint15>gnome-print
nautilus>nautilus-mozilla
tcl>postgresql-tcl
libtermcap>bash
modutils>vixie-cron
ypbind>yp-tools
ghostscript-fonts>ghostscript
usermode>util-linux
control-center>xscreensaver
kdemultimedia-arts>kdemultimedia-libs
initscripts>util-linux
XFree86-libs>XFree86-Mesa-libGL
xorg-x11-libs>xorg-x11-Mesa-libGL
mysql>perl-DBD-MySQL
ghostscript>gimp-print
bind>bind-utils
perl>mod_perl
perl>perl-Filter
coreutils>pam
perl>mrtg
perl-Date-Calc>perl-Bit-Vector
glibc-debug>glibc-devel
xinitrc>XFree86
xinitrc>xorg-x11
xemacs>apel-xemacs
gimp>gimp-print-plugin
redhat-lsb>redhat-lsb
info>ncurses
aspell>aspell-en
dbus>dbus-glib
xemacs>xemacs-sumo
ncurses>gpm
cyrus-sasl>openldap
lvm2>kernel
initscripts>kernel
initscripts>kernel-smp
httpd>httpd-suexec
php>php-pear
gnome-python2>gnome-python2-bonobo
openoffice.org-libs>openoffice.org
gtk+>gdk-pixbuf
nautilus>nautilus-cd-burner
hicolor-icon-theme>gtk2
gtk2>scim-libs
'''

WHITE_TUP = map(lambda x: tuple(x.split('>')), WHITEOUT.split())
