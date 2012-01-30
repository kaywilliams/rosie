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

import cPickle
import hashlib
import yum

from centosstudio.errors         import CentOSStudioError
from centosstudio.event          import Event
from centosstudio.util.repo      import YumRepo
from centosstudio.modules.shared import (RpmBuildMixin, 
                                          Trigger, 
                                          TriggerContainer)

class ReleaseRpmEventMixin(RpmBuildMixin):
  release_mixin_version = "1.21"

  def __init__(self, rpmxpath=None): # call after creating self.DATA
    self.conditionally_requires.add('packages')
    self.rpmxpath = rpmxpath or '.'
    self.conditionally_requires.add('gpg-signing-keys')

    RpmBuildMixin.__init__(self,
      '%s-release' % self.name,   
      "The %s-release package provides yum configuration for the  " 
      "%s repository." % (self.name, self.fullname),
      "%s repository configuration" % self.fullname,
      requires = ['coreutils']
    )

  def setup(self, webpath, files_cb=None, files_text="downloading files",
            **kwargs):
    self.DATA['variables'].append('release_mixin_version')
    self.DATA['config'].append(self.rpmxpath)

    self.webpath = webpath
    self.masterrepo = '%s-%s' % (self.name, 
                      hashlib.md5(self.solutionid).hexdigest()[-6:])
    self.files_cb = files_cb
    self.files_text = files_text

    RpmBuildMixin.setup(self, **kwargs)

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
    self.pklfile = self.mddir/'gpgkeys.pkl'
    self.gpgkey_dir = self.SOFTWARE_STORE/'gpgkeys'

    if not self.cvars['gpgcheck-enabled']:
      return

    repos = self.cvars['repos'].values()
    if 'gpg-signing-keys' in self.cvars: 
      repos = (repos +
              # using a dummy repo since rpmbuild repo not yet created
               [YumRepo(id='dummy', gpgkey=self.cvars['gpg-signing-keys']
                                                     ['pubkey'])])

    for repo in repos:
      for url in repo.gpgkey:
        try:
          self.io.add_fpath(url,
            self.gpgkey_dir,
            destname='RPM-GPG-KEY-%s' % \
              yum.YumBase()._retrievePublicKey(url, yum.yumRepo.YumRepository(
              str(repo)))[0]['hexkeyid'].lower(),
            id='gpgkeys')
        except yum.Errors.YumBaseError, e:
          raise MissingGPGKeyError(file=url, repo=repo.id)

  def run(self):
    for path in [ self.pklfile, self.gpgkey_dir ]:
      path.rm(recursive=True, force=True)
    RpmBuildMixin.run(self)

  def generate(self):
    for what in ['gpgkeys']:
      self.io.process_files(cache=True, callback=self.files_cb, 
                            text=self.files_text, what=what)

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
      self.pklfile.rm(force=True)
      return []

    # get list of keys
    gpgkeys = set(self.io.list_output(what='gpgkeys'))

    # cache for future
    fo = self.pklfile.open('wb')
    cPickle.dump(gpgkeys, fo, -1)
    self.DATA['output'].append(self.pklfile)
    fo.close()

    # create gpgkey list for use by yum sync plugin
    listfile = self.gpgkey_dir/'gpgkey.list'
    lines = [x.basename for x in gpgkeys]
    listfile.write_lines(lines)
    self.DATA['output'].append(listfile)

    # convert keys to remote urls for use in repofile
    remotekeys = set([(self.webpath/x[len(self.SOFTWARE_STORE+'/'):])
                       for x in gpgkeys])

    return remotekeys

  def apply(self):
    self.rpm._apply()
    if self.pklfile.exists():
      fo = self.pklfile.open('rb')
      self.cvars['gpgkeys'] = cPickle.load(fo)
      fo.close()
    else:
      self.cvars['gpgkeys'] = []

class MissingGPGKeyError(CentOSStudioError):
  message = "Cannot find GPG key specified for the '%(repo)s' package repository: '%(file)s'"
