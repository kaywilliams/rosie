from systembuilder.locals import LocalsDict, REMOVE

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
    '  for repo in conduit._base.repos.listEnabled():',
    '    if repo.id == conduit.confString(\'main\', \'masterrepo\', default=\'base\'):',
    '      continue',
    '    conduit.info(2, "[%s] Ignoring non-master repo \'%s\'" % (PLUGIN_NAME, repo.id))',
    '    conduit._base.repos.disableRepo(repo.id)',
    '',
    'def postresolve_hook(conduit):',
    '  availpkgs  = conduit._base.doPackageLists(\'available\')',
    '',
    '  for tsmem in conduit.getTsInfo().getMembers():',
    '    if tsmem.pkgtup in [ x.pkgtup for x in availpkgs.available ] or \\',
    '       tsmem.pkgtup in [ x.pkgtup for x in availpkgs.reinstall_available ]:',
    '      if tsmem.ts_state == \'e\':',
    '        raise PluginYumExit("[%s] Cannot remove package \'%s\'" % (PLUGIN_NAME, tsmem.po))',
    '',
    'class StrictSyncCommand:',
    '  def getNames(self):',
    '    return [\'sync\', \'strict-sync\']',
    '',
    '  def getSummary(self):',
    '    return "syncs installed packages with master repository"',
    '',
    '  def doCheck(self, base, basecmd, extcmds):',
    '    pass',
    '',
    '  def doCommand(self, base, basecmd, extcmds):',
    '    try:',
    '      newpkgs = base.doPackageLists(\'available\').available',
    '      oldpkgs = base.doPackageLists(\'extras\').extras',
    '',
    '      # add any available package that is not yet installed',
    '      for po in newpkgs:',
    '        base.verbose_logger.info("[%s] adding available package \'%s\'" % (PLUGIN_NAME, po))',
    '        base.install(po)',
    '',
    '      # remove any installed package that is not available',
    '      for po in oldpkgs:',
    '        base.verbose_logger.info("[%s] removing installed package \'%s\'" % (PLUGIN_NAME, po))',
    '        base.remove(po)',
    '',
    '      if len(newpkgs) > 0 or len(oldpkgs) > 0:',
    '        return 2, [\'Package(s) to install or remove\']',
    '      else:',
    '        return 0, [\'Nothing to do\']',
    '',
    '    except YumBaseError, e:',
    '      return 1, [str(e)]',
    '',
    'def config_hook(conduit):',
    '  conduit.registerCommand(StrictSyncCommand())',
  ],
}


L_YUM_PLUGIN = {
  "CentOS": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "Fedora": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
  "RedHat": LocalsDict({
    '0': PLUGIN_DEFAULTS,
  }),
}
