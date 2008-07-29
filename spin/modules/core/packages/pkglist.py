#
# Copyright (c) 2007, 2008
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
import re
import rpmUtils.arch

from rendition import depsolver
from rendition import difftest

from spin.callback  import BuildDepsolveCallback
from spin.constants import KERNELS
from spin.event     import Event
from spin.logging   import L1

from spin.modules.shared import idepsolver

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['PkglistEvent'],
  description = 'depsolves comps.xml to create a package list',
  group       = 'packages',
)

YUMCONF_HEADER = [
  '[main]',
  'cachedir=',
  'logfile=/depsolve.log',
  'debuglevel=0',
  'errorlevel=0',
  'gpgcheck=0',
  'tolerant=1',
  'exactarch=1',
  'reposdir=/',
  '\n',
]

NVRA_REGEX = re.compile('(?P<name>.+)'    # rpm name
                        '-'
                        '(?P<version>.+)' # rpm version
                        '-'
                        '(?P<release>.+)' # rpm release
                        '\.'
                        '(?P<arch>.+)')   # rpm architecture

INCREMENTAL_DEPSOLVE = True

class PkglistEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pkglist',
      parentid = 'packages',
      provides = ['pkglist'],
      requires = ['required-packages', 'repos', 'user-required-packages'],
      conditionally_requires = ['pkglist-excluded-packages'],
      version = '0.2',
    )

    self.dsdir = self.mddir / 'depsolve'
    self.pkglistfile = self.mddir / 'pkglist'

    self.DATA = {
      'config':    ['.'],
      'variables': ['cvars[\'required-packages\']'],
      'input':     [],
      'output':    [],
    }
    self.docopy = self.config.pathexists('text()')

  def setup(self):
    self.diff.setup(self.DATA)

    # setup if copying pkglist
    if self.docopy:
      self.io.add_xpath('.', self.mddir, id='pkglist')
      self.pkglistfile = self.io.list_output(what='pkglist')[0]
      return

    # setup if creating pkglist
    self.pkglistfile = self.mddir / 'pkglist'

    # add relevant input/variable sections, if interesting
    for repoid, repo in self.cvars['repos'].items():
      for attr in ['baseurl', 'mirrorlist', 'exclude',
                   'includepkgs', 'enabled']:

        if getattr(repo, attr):
          self.DATA['variables'].append('cvars[\'repos\'][\'%s\'].%s'
                                        % (repoid, attr))

      self.DATA['input'].append(repo.localurl/'repodata')

  def run(self):
    # copy pkglist
    if self.docopy:
      self.io.sync_input(cache=True)
      self.log(1, L1("reading supplied package list"))
      if self.dsdir.exists():
        self.dsdir.rm(recursive=True)
      return

    # create pkglist
    if not self.dsdir.exists():
      self.dsdir.mkdirs()

    self._verify_repos()
    repoconfig = self._create_repoconfig()
    required_packages = self.cvars.get('required-packages', [])
    user_required = self.cvars.get('user-required-packages', [])

    if INCREMENTAL_DEPSOLVE:
      old_packages = []
      difftup = self.diff.variables.difference('cvars[\'required-packages\']')
      if difftup:
        prev, curr = difftup
        if ( prev is None or
             isinstance(prev, difftest.NewEntry) or
             isinstance(prev, difftest.NoneEntry) ):
          prev = []
        if prev:
          old_packages.extend([ x for x in prev if x not in curr ])

      pkgtups = idepsolver.resolve(all_packages = required_packages,
                                   old_packages = old_packages,
                                   required = user_required,
                                   config = str(repoconfig),
                                   root = str(self.dsdir),
                                   arch = self.arch,
                                   callback = BuildDepsolveCallback(self.logger),
                                   logger = self.logger)
    else:
      self.log(1, L1("resolving package dependencies"))
      pkgtups = depsolver.resolve(packages = required_packages,
                                  required = user_required,
                                  config = str(repoconfig),
                                  root = str(self.dsdir),
                                  arch = self.arch,
                                  callback = BuildDepsolveCallback(self.logger))

    self.log(1, L1("pkglist closure achieved in %d packages" % len(pkgtups)))

    pkglist = []
    for n,a,_,v,r in pkgtups:
      pkglist.append('%s-%s-%s.%s' % (n,v,r,a))
    pkglist.sort()

    self.log(1, L1("writing pkglist"))
    self.pkglistfile.write_lines(pkglist)

    self.DATA['output'].extend([self.dsdir, self.pkglistfile, repoconfig])

  def apply(self):
    self.io.clean_eventcache()
    try:
      self.cvars['pkglist'] = self.pkglistfile.read_lines()
    except Exception, e:
      raise RuntimeError(str(e))

  def verify_pkglistfile_exists(self):
    "pkglist file exists"
    self.verifier.failUnlessExists(self.pkglistfile)

  def verify_kernel_arch(self):
    "kernel arch matches arch in config"
    matched = False
    for pkg in self.cvars['pkglist']:
      n,v,r,a = NVRA_REGEX.match(pkg).groups()
      if n not in KERNELS: continue
      self.verifier.failUnlessEqual(rpmUtils.arch.getBaseArch(a), self.basearch,
        "the base arch of kernel package '%s' does not match the specified "
        "base arch '%s'" % (pkg, self.basearch))
      matched = True

    self.verifier.failUnless(matched, "no kernel package found")

  def _verify_repos(self):
    for repoid, repo in self.cvars['repos'].items():
      for f in self.diff.input.difference().keys():
        if f.startswith(repo.localurl/'repodata'):
          (self.dsdir/repoid).rm(recursive=True, force=True)
          break

  def _create_repoconfig(self):
    repoconfig = self.mddir / 'depsolve.repo'
    if repoconfig.exists():
      repoconfig.remove()
    conf = []
    conf.extend(YUMCONF_HEADER)
    if self.cvars['pkglist-excluded-packages']:
      line = 'exclude=' + ' '.join(self.cvars['pkglist-excluded-packages'])
      conf.append(line)
    for repo in self.cvars['repos'].values():
      conf.extend(repo.lines(pretty=True, baseurl=repo.localurl, mirrorlist=None))
      conf.append('\n')
    repoconfig.write_lines(conf)
    return repoconfig
