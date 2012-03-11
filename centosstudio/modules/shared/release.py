#
# Copyright (c) 2011
# CentOS Solutions, Inc. All rights reserved.
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

import hashlib
import yum

from centosstudio.errors         import CentOSStudioEventError
from centosstudio.event          import Event
from centosstudio.util.repo      import YumRepo
from centosstudio.modules.shared import (ShelveMixin, MkrpmRpmBuildMixin,
                                         Trigger, TriggerContainer)

class ReleaseRpmEventMixin(MkrpmRpmBuildMixin, ShelveMixin):
  release_mixin_version = "1.23"

  def __init__(self, rpmxpath=None): # call after creating self.DATA
    self.conditionally_requires.add('packages')
    self.rpmxpath = rpmxpath or '.'
    self.conditionally_requires.add('gpg-signing-keys')

    MkrpmRpmBuildMixin.__init__(self,
      '%s-release' % self.name,   
      "The %s-release package provides yum configuration for the  " 
      "%s repository." % (self.name, self.fullname),
      "%s repository configuration" % self.fullname,
      requires = ['coreutils']
    )

    ShelveMixin.__init__(self)

  def setup(self, webpath, files_cb=None, files_text="downloading files",
            **kwargs):
    self.DATA['variables'].append('release_mixin_version')
    self.DATA['config'].append(self.rpmxpath)

    # use webpath property if already set (i.e. in test-install and test-update
    # modules) otherwise use passed in value
    if not hasattr(self, 'webpath'): self.webpath = webpath

    self.masterrepo = '%s-%s' % (self.name, 
                      hashlib.md5(self.solutionid).hexdigest()[-6:])
    self.files_cb = files_cb
    self.files_text = files_text

    MkrpmRpmBuildMixin.setup(self, **kwargs)

    self.DATA['variables'].extend(['masterrepo', 'webpath'])

    # setup yum plugin (unless disabled or application-type solution)
    if (self.config.getbool('%s/updates/@sync' % self.rpmxpath, True) and
        self.type == 'system'):
      self.plugin_lines = self.locals.L_YUM_PLUGIN['plugin']
      self.plugin_hash = hashlib.sha224('/n'.join(
                         self.plugin_lines)).hexdigest()
      # hackish - do %s replacement for masterrepo
      map = { 'masterrepo': self.masterrepo }
      self.plugin_conf_lines = [ x % map for
                                 x in self.locals.L_YUM_PLUGIN['config'] ]
      self.plugin_conf_hash = hashlib.sha224('/n'.join(
                              self.plugin_conf_lines)).hexdigest()
      self.DATA['variables'].extend(['plugin_hash', 'plugin_conf_hash'])


    # setup gpgkeys
    self.cvars['gpgcheck-enabled'] = self.config.getbool(
                                     '%s/updates/@gpgcheck' % self.rpmxpath,
                                     True)
    self.gpgkey_dir = self.SOFTWARE_STORE/'gpgkeys'

    if not self.cvars['gpgcheck-enabled']:
      return

    repos = self.cvars['repos'].values()
    if 'gpg-signing-keys' in self.cvars: 
      repos = (repos +
              # using a dummy repo since rpmbuild repo not yet created
               [YumRepo(id='dummy', gpgkey=self.cvars['gpg-signing-keys']
                                                     ['pubkey'])])

    self.gpgkeys = {}
    for repo in repos:
      for url in repo.gpgkey:
        try:
          yb = yum.YumBase()
          yb.verbose_logger = self.logger 
          id = yb._retrievePublicKey(url, yum.yumRepo.YumRepository(
               str(repo)))[0]['hexkeyid']
          self.gpgkeys[id] = url
        except yum.Errors.YumBaseError, e:
          message = ("An error occurred attempting to retrieve the GPG key "
                     "for the '%s' package repository. The error message "
                     "is printed below:\n%s" % (repo.id, e))
          raise GPGKeyError(message=message)

    self.keyids = self.gpgkeys.keys() # only track changes to keyids, not urls
    self.DATA['variables'].append('keyids')

  def run(self):
    for path in [ self.shelvefile, self.gpgkey_dir ]:
      path.rm(recursive=True, force=True)
    MkrpmRpmBuildMixin.run(self)

  def generate(self):
    if self.cvars['gpgcheck-enabled']:
      # download gpgkeys - we're doing this manually rather than using 
      # process_files because we don't want to track keys as input. Doing so 
      # causes the release rpm to be regenerated each time the url to an input 
      # gpgkey changes, and we want the release rpm to be immune to this class
      # of changes
      self.gpgkey_dir.mkdirs()
      self.localkeys = []
      for url in self.gpgkeys.values():
        url.cp(self.gpgkey_dir)
        local = self.gpgkey_dir / url.basename
        self.localkeys.append(local)
        self.DATA['output'].append(local)

    # generate repofile
    self._generate_repofile()
    if (self.config.getbool('%s/updates/@sync' % self.rpmxpath, True) and
        self.type == "system"):
      self.rpm.requires.append('yum')
      self._include_sync_plugin()

  def _generate_repofile(self):
    repofile = ( self.rpm.source_folder / 'etc/yum.repos.d/%s.repo' % self.name )

    lines = []
    # include system repo
    if self.webpath is not None:
      baseurl = self.webpath
      lines.extend([ '[%s]' % self.masterrepo, 
                     'name      = %s - %s' % (self.fullname, self.basearch),
                     'baseurl   = %s' % baseurl,
                     'gpgcheck = %s' % (self.cvars['gpgcheck-enabled']),
                     ])
      lines.append('gpgkey = %s' % ', '.join(self._gpgkeys()))

    if len(lines) > 0:
      repofile.dirname.mkdirs()
      repofile.write_lines(lines)

      self.DATA['output'].append(repofile)

  def _include_sync_plugin(self):
    # config
    configfile = (self.rpm.source_folder / 'etc/yum/pluginconf.d/sync.conf')
    configfile.dirname.mkdirs()
    configfile.write_lines(self.plugin_conf_lines)

    # cronjob
    #cronfile = (self.rpm.source_folder / 'etc/cron.daily/sync.cron')
    #cronfile.dirname.mkdirs()
    #cronfile.write_lines(self.locals.L_YUM_PLUGIN['cron'])

    # plugin
    plugin = (self.rpm.source_folder / 'usr/lib/yum-plugins/sync.py')
    plugin.dirname.mkdirs()
    plugin.write_lines(self.plugin_lines)

  def _gpgkeys(self):
    if not self.cvars['gpgcheck-enabled']:
      self.shelvefile.rm(force=True)
      return []

    # cache for future
    self.shelve('gpgkeys', self.localkeys)

    # create gpgkey list for use by yum sync plugin
    listfile = self.gpgkey_dir/'gpgkey.list'
    lines = [x.basename for x in self.localkeys]
    listfile.write_lines(lines)
    self.DATA['output'].append(listfile)

    # convert keys to remote urls for use in repofile
    remotekeys = set([(self.webpath/x[len(self.SOFTWARE_STORE+'/'):])
                       for x in self.localkeys])

    return remotekeys

  def apply(self):
    MkrpmRpmBuildMixin.apply(self) 
    self.cvars['gpgkeys'] = self.unshelve('gpgkeys', [])

class GPGKeyError(CentOSStudioEventError):
  message = "%(message)s"
