from deploy.locals import LocalsDict, REMOVE

__all__ = ['L_YUM_PLUGIN']

PLUGIN_DEFAULTS = {
  'config': [
    '[main]',
    'enabled = 1',
    'masterrepo = %(masterrepo)s',
  ],
  'cron': [
    '#!/bin/sh',
    '/usr/bin/yum sync',
  ],
  'plugin': [
    'import os',
    'import yum',
    'import yum.i18n',
    '_ = yum.i18n._',
    '',
    'from urlgrabber.grabber import URLGrabber, URLGrabError, default_grabber',
    'from yum.Errors import YumBaseError',
    'from yum.plugins import PluginYumExit, TYPE_CORE, TYPE_INTERACTIVE',
    '',
    'requires_api_version = \'2.6\'',
    'plugin_type = (TYPE_CORE, TYPE_INTERACTIVE)',
    '',
    'PLUGIN_NAME = \'sync\'',
    '',
    '# disable all repos except the master repo',
    'def prereposetup_hook(conduit):',
    '  conduit._base.cleanMetadata()',
    '  for repo in conduit._base.repos.listEnabled():',
    '    if repo.id == conduit._base.masterrepo:',
    '      continue',
    '    conduit.info(2, "[%s] Ignoring repo \'%s\'" % (PLUGIN_NAME, repo.id))',
    '    conduit._base.repos.disableRepo(repo.id)',
    '',
    'def preresolve_hook(conduit):',
    '  # check prior to depsolving to see if user list of packages to remove',
    '  # includes any packages in the master repository',
    '  _txCheck(conduit)',
    '',
    'def postresolve_hook(conduit):',
    '  # check again after depsolving to see if any package is being removed',
    '  # for depsolving reasons that is in the master repository (this may be',
    '  # impossible, but just to be sure...)',
    '  _txCheck(conduit)',
    '',
    'def _txCheck(conduit):',
    '  # perform a check on the transaction to see if we\'re trying to',
    '  # remove a package that we\'re not supposed to be removing',
    '  availpkgs = conduit._base.doPackageLists(\'available\')',
    '',
    '  for tsmem in conduit.getTsInfo().getMembers():',
    '    if tsmem.pkgtup in [ x.pkgtup for x in availpkgs.available ] or \\',
    '       tsmem.pkgtup in [ x.pkgtup for x in availpkgs.reinstall_available ]:',
    '      if tsmem.ts_state == \'e\':',
    '        raise PluginYumExit("[%s] Cannot remove package \'%s\'" % (PLUGIN_NAME, tsmem.po))',
    '',
    '',
    'class SyncCommand:',
    '  def getNames(self):',
    '    return [\'sync\',]',
    '',
    '  def getSummary(self):',
    '    return "syncs installed packages with master repository"',
    '',
    '  def doCheck(self, base, basecmd, extcmds):',
    '    pass',
    '',
    '  def doCommand(self, base, basecmd, extcmds):',
    '    def callback(reason, amount, total, key, client_data): pass',
    '',
    '    ##### sync gpgkeys #####',
    '    repo = base.repos.getRepo(base.masterrepo)',
    '    if repo.gpgcheck:',
    '      self._sync_gpgkeys(repo, base, callback)',
    '',
    '    ##### sync packages #####',
    '    base.verbose_logger.log(yum.logginglevels.INFO_2, _(\'Synchronizing packages\') ) ',
    '',
    '    try:',
    '      oldpkgs = base.doPackageLists(\'extras\').extras',
    '      newpkgs = base.doPackageLists(\'available\', showdups=True).available',
    '',
    '      # remove any installed package that is not available',
    '      newpkg_nevrs = ["%s-%s-%s-%s" % (x.name, x.epoch, x.version,', 
    '                      x.release) for x in newpkgs]',
    '      for po in oldpkgs:',
    '        if ("%s-%s-%s-%s" % (po.name, po.epoch, po.version, po.release)',
    '            not in newpkg_nevrs): # filter pkgs with arch-only changes',
    '          base.verbose_logger.log(yum.logginglevels.INFO_2, "[%s] removing installed package \'%s\'" % (PLUGIN_NAME, po))',
    '          base.remove(po)',
    '',
    '      # add any available package that is not yet installed',
    '      oldpkg_nevrs = ["%s-%s-%s-%s" % (x.name, x.epoch, x.version,',
    '                      x.release) for x in oldpkgs]',
    '      for po in newpkgs:',
    '        if ("%s-%s-%s-%s" % (po.name, po.epoch, po.version, po.release)',
    '            not in oldpkg_nevrs): # filter pkgs with arch-only changes',
    '          base.verbose_logger.log(yum.logginglevels.INFO_2, "[%s] adding available package \'%s\'" % (PLUGIN_NAME, po))',
    '          base.install(po)',
    '',
    '      if len(newpkgs) > 0 or len(oldpkgs) > 0:',
    '        return 2, [\'Package(s) to install or remove\']',
    '      else:',
    '        return 0, [\'Nothing to do\']',
    '',
    '    except YumBaseError, e:',
    '      return 1, [str(e)]',
    '',
    '  def _sync_gpgkeys(self, repo, base, callback):',
    '    base.verbose_logger.log(yum.logginglevels.INFO_2, _(\'Synchronizing keys\') ) ',
    '',
    '    # get list of available_keys',
    '    listurl = repo.urls[0] + \'gpgkeys/gpgkey.list\'',
    '',
    '    try:',
    '      ug = URLGrabber(**repo._default_grabopts())',
    '      keyfiles = ug.urlread(listurl).split(\'\\n\')',
    '      keyfiles = filter(lambda x: len(x)>0, keyfiles) # remove empty strings',
    ' ',
    '    except URLGrabError, e:',
    '      base.verbose_logger.log(yum.logginglevels.INFO_2, _(',
    '        \"Unable to retrieve GPG key list \'%s\': %s\") % ',
    '        (listurl, yum.i18n.to_unicode(str(e),)))          ',
    '      keyfiles = None ',
    '',
    '    # get info about available keys',
    '    if keyfiles:',
    '      available_keys = {} # dict of keyinfos keyed by hexkeyid and timestamp',
    '      keys_changed = False # used to provide a log message if no changes',
    '',
    '      for keyfile in keyfiles:',
    '        keyurl = os.path.dirname(listurl) + "/" + keyfile',
    '        try:',
    '          rawkey = ug.urlread(keyurl)',
    '        except URLGrabError, e:',
    '          raise YumBaseError(_(',
    '             \"GPG key retrieval failed from \'%s\': %s\") % ',
    '            (keyurl, yum.i18n.to_unicode(str(e))))',
    '',
    '        try:',
    '          keys_info = yum.misc.getgpgkeyinfo(rawkey, multiple=True)',
    '        except ValueError, e:',
    '          raise YumBaseError(_(\"Invalid GPG Key from \'%s\': %s\") %',
    '                                 (keyurl, yum.i18n.to_unicode(str(e))))',
    '        for keyinfo in keys_info:',
    '          thiskey = {}',
    '          for info in (\'keyid\', \'timestamp\', \'userid\',',
    '                       \'fingerprint\', \'raw_key\'):',
    '              if info not in keyinfo:',
    '                  raise (YumBaseError, ',
    '                    _(\'GPG key parsing failed: key does not have value %s\')',
    '                    + info)',
    '              thiskey[info] = keyinfo[info]',
    '          thiskey[\'hexkeyid\'] = yum.misc.keyIdToRPMVer(',
    '                                keyinfo[\'keyid\']).upper()',
    '',
    '          available_keys[(thiskey[\'hexkeyid\'].lower(), ',
    '                          thiskey[\'timestamp\'])] = thiskey',
    '',
    '      # get info about installed keys',
    '      installed_keys = {}',
    '      for hdr in base.ts.dbMatch(\'name\', \'gpg-pubkey\'):',
    '        installed_keys[(hdr[\'version\'], int(hdr[\'release\'], 16))] = hdr',
    '',
    '      # add new keys',
    '      for key in available_keys:',
    '        if key not in installed_keys:',
    '          keys_changed = True',
    '          base.verbose_logger.log(yum.logginglevels.INFO_2, _(\'Importing key %s "%s" \') %',
    '                                (available_keys[key][\'hexkeyid\'].lower(),',
    '                                 yum.i18n.to_unicode(',
    '                                 available_keys[key][\'userid\']),))          ',
    '          result = base.ts.pgpImportPubkey(',
    '                   yum.misc.procgpgkey(available_keys[key][\'raw_key\']))',
    '          if result != 0:',
    '              raise (YumBaseError, ',
    '                    _(\'Key import failed (code %d)\') % result)',
    '',
    '      # remove obsolete keys',
    '      for key in installed_keys:',
    '        if key not in available_keys:',
    '          keys_changed = True',
    '          base.verbose_logger.log(yum.logginglevels.INFO_2, _(\'Removing GPG key %s "%s" \') %',
    '                              (installed_keys[key][\'version\'].lower(),',
    '                               yum.i18n.to_unicode(',
    '                               installed_keys[key][\'summary\']),))          ',
    '          base.ts.addErase(\'gpg-pubkey-%s-%s\' % ',
    '                          (installed_keys[key][\'version\'], ',
    '                           installed_keys[key][\'release\']) )',
    '      errors = base.ts.run(callback, \'\')      ',
    '      if errors:',
    '        raise (YumBaseError, (_(\'GPG key removal failed: %s\') % errors))',
    '',
    '      if not keys_changed:',
    '        base.verbose_logger.log(yum.logginglevels.INFO_2, _(\'Nothing to do\'))',
    '',
    '    else:',
    '      base.verbose_logger.log(yum.logginglevels.INFO_2, _(\'No keys to sync\'))',
    '',
    'def config_hook(conduit):',
    '  conduit._base.masterrepo = conduit.confString(',
    '                             \'main\', \'masterrepo\', default=\'base\')',
    '  conduit.registerCommand(SyncCommand())',
  ],
}


L_YUM_PLUGIN = {
  "centos": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "CentOS": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "CentOS Linux": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "Fedora": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "Red Hat Enterprise Linux": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "Red Hat Enterprise Linux Server": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "Red Hat Enterprise Linux Client": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
}
