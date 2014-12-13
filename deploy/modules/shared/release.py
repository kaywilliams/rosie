#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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

from deploy.errors         import DeployEventError
from deploy.event          import Event, DummyConfig
from deploy.event.fileio   import InputFileError
from deploy.modules.shared import (MkrpmRpmBuildMixin, GPGKeysEventMixin,
                                   Trigger, TriggerContainer, DeployRepo)
from deploy.util           import rxml

class ReleaseRpmEventMixin(MkrpmRpmBuildMixin, GPGKeysEventMixin):
  release_mixin_version = "1.29"

  def __init__(self): # call after creating self.DATA
    self.rpmconf = self.config.getxpath('release-rpm', 
                                        DummyConfig(self._config))

    self.conditionally_requires.add('packages')
    self.conditionally_requires.add('gpg-signing-keys')

    MkrpmRpmBuildMixin.__init__(self)

  def setup(self, webpath, files_cb=None, files_text="downloading files",
            force_release=None):
    self.DATA['variables'].add('release_mixin_version')
    self.DATA['config'].add('release-rpm')

    # use webpath property if already set (i.e. in test-install and test-update
    # modules) otherwise use passed in value
    if not hasattr(self, 'webpath'): self.webpath = webpath
   
    self.masterrepo = '%s-%s' % (self.name, 
                      hashlib.md5(self.build_id).hexdigest()[-6:])

    # if you change the values below, also change yum_plugin locals
    self.keydir = 'gpgkeys'
    self.keylist = 'gpgkey.list'

    self.local_keydir = self.OUTPUT_DIR / self.keydir
    self.remote_keydir = self.webpath / self.keydir

    self.files_cb = files_cb
    self.files_text = files_text

    name = '%s-release' % self.name   
    desc = ("The %s-release package provides yum configuration for the  " 
            "%s repository." % (self.name, self.fullname))
    summary =  "%s repository configuration" % self.fullname
    requires = ['coreutils']

    MkrpmRpmBuildMixin.setup(self, name=name, desc=desc, summary=summary,
                             requires=requires, force_release=force_release)

    self.DATA['variables'].update(['masterrepo', 'webpath', 'local_keydir', 
                                   'remote_keydir', 'keylist'])

    # setup yum plugin (unless disabled or non-system repo)
    if (self.rpmconf.getbool('updates/@sync', True) and
        self.type == 'system'):
      self.plugin_lines = self.locals.L_YUM_PLUGIN['plugin']
      self.plugin_hash = hashlib.sha224('/n'.join(
                         self.plugin_lines)).hexdigest()
      # hackish - do %s replacement sync plugin
      map = { 'masterrepo': self.masterrepo, }
      self.plugin_conf_lines = [ x % map for
                                 x in self.locals.L_YUM_PLUGIN['config'] ]
      self.plugin_conf_hash = hashlib.sha224('/n'.join(
                              self.plugin_conf_lines)).hexdigest()
      self.DATA['variables'].update(['plugin_hash', 'plugin_conf_hash'])

    # setup gpgkeys
    self.cvars['gpgcheck-enabled'] = self.rpmconf.getbool(
                                     'updates/@gpgcheck', True)

    if not self.cvars['gpgcheck-enabled']:
      return

    self.repos = self.cvars['repos'].values()
    if 'gpg-signing-keys' in self.cvars:
      # append a dummy repo since rpmbuild repo not yet created
      self.repos.append(DeployRepo(id='dummy', 
                        gpgkey=self.cvars['gpg-signing-keys']['pubkey'],
                        download='true'))

    GPGKeysEventMixin.setup(self) # set self.repos before calling

  def run(self):
    self.local_keydir.rm(recursive=True, force=True)
    MkrpmRpmBuildMixin.run(self)

  def generate(self):
    if self.cvars['gpgcheck-enabled']:
      # download gpgkeys - we're doing this manually rather than using 
      # process_files because we don't want to track keys as input. Doing so 
      # causes the release rpm to be regenerated each time the url to an input 
      # gpgkey changes, and we want the release rpm to be immune to this class
      # of changes
      self.local_keydir.mkdirs(mode=0700)
      self.local_keydir.chown(0,0)
      self.keys = []
      for filename, url in self.gpgkeys.iteritems():
        try:
          url.cp(self.local_keydir/filename, mirror=True)
        except Exception, e:
          message = ("An error occurred attempting to retrieve the GPG key "
                     "located at '%s'. The error message is printed below:\n"
                     "%s" % (url, e))
          raise GPGKeyError(message=message)
        self.keys.append(filename)
        self.DATA['output'].add(self.local_keydir / filename)

    # generate repofile
    self._generate_repofile()
    if (self.rpmconf.getbool('updates/@sync', True) and
        self.type == "system"):
      self.rpm.requires.append('yum')
      self._include_sync_plugin()

  def _generate_repofile(self):
    repofile = ( self.rpm.source_folder / 'etc/yum.repos.d/%s.repo' % self.name )
    repofile.rm(force=True) # start clean so publish hardlinking works

    lines = []
    # include system repo
    if self.webpath is not None:
      baseurl = self.webpath
      lines.extend([ '[%s]' % self.masterrepo, 
                     'name      = %s - %s' % (self.fullname, self.arch),
                     'baseurl   = %s' % baseurl,
                     'gpgcheck = %s' % (self.cvars['gpgcheck-enabled']),
                     ])
      lines.append('gpgkey = %s' % ', '.join(self._gpgkeys()))
      if self.rpmconf.getxpath('updates/@sslverify', None):
        lines.append('sslverify = %s' % 
                     self.rpmconf.getbool('updates/@sslverify'))

    if len(lines) > 0:
      repofile.dirname.mkdirs()
      repofile.write_lines(lines)

      # include repofile at root of repository
      pubfile = self.OUTPUT_DIR / 'repo.conf'
      repofile.cp(pubfile, force=True, preserve=True)

      self.DATA['output'].update([repofile, pubfile])

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
      return []

    # create gpgkey list for use by yum sync plugin
    listfile = self.local_keydir / self.keylist
    listfile.write_lines(self.keys)
    self.DATA['output'].add(listfile)

    # convert keys to remote urls for use in repofile
    remotekeys = set([ self.remote_keydir / x for x in self.keys])

    return remotekeys

  def apply(self):
    MkrpmRpmBuildMixin.apply(self)


class GPGKeyError(DeployEventError):
  message = "%(message)s"
