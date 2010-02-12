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
from StringIO import StringIO

from rendition import pps

from systembuilder.event     import Event
from systembuilder.validate  import InvalidConfigError

from systembuilder.modules.shared import RpmBuildMixin, Trigger, TriggerContainer

import md5

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['ConfigEvent'],
  description = 'creates a configuration RPM',
  group       = 'rpmbuild',
)

class ConfigEvent(RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'config',
      parentid = 'rpmbuild',
      version = '0.99',
      provides = ['rpmbuild-data'],
      requires = ['input-repos'],
      conditionally_requires = ['web-path', 'gpgsign-public-key'],
    )

    RpmBuildMixin.__init__(self,
      '%s-config' % self.name,
      "The %s-config provides scripts and supporting files for configuring "
      "the %s distribution." % (self.name, self.fullname),
      "%s configuration script and supporting files" % self.fullname,
      requires = ['coreutils', 'policycoreutils']
    )

    self.scriptdir   = self.rpm.build_folder/'scripts'
    self.filedir     = self.rpm.build_folder/'files'
    self.filerelpath = pps.path('usr/share/%s/files' % self.name)

    self.DATA = {
      'variables': ['name', 'fullname', 'distributionid', 'rpm.release',
                    'cvars[\'web-path\']', 'cvars[\'gpgsign-public-key\']',],
      'config':    ['.'],
      'input':     [],
      'output':    [self.rpm.build_folder],
    }

  def validate(self):
    for file in self.config.xpath('file', []):
      # if using text mode, a destname must be specified; otherwise,
      # we don't know what to name the file
      if file.get('@content', None) and not file.get('@destname', None):
        raise InvalidConfigError(self.config.getroot().file,
          "'text' content type specified without accompanying 'destname' "
          "attribute:\n %s" % file)

  def setup(self):
    self.rpm.setup_build()


    # add all scripts as input so if they change, we rerun
    for script in self.config.xpath('script',  []) + \
                  self.config.xpath('trigger', []):
      if script.get('@content', 'filename') != 'text':
        self.DATA['input'].append(script.text)

    # TODO move to run function?
    self.scriptdir.mkdirs()
    self.filedir.mkdirs()
    for file in self.config.xpath('files', []):
      text = file.text
      if file.get('@content', 'filename') == 'text':
        # if the content is 'text', write the string to a file and set
        # text to that value
        fn = self.filedir/file.get('@destname')
        if not fn.exists() or fn.md5sum() != md5.new(text).hexdigest():
          fn.write_text(text)
        text = fn

      self.io.add_fpath(text, ( self.rpm.source_folder //
                                self.filerelpath //
                                file.get('@destdir',
                                         '/usr/share/%s/files' % self.name) ),
                              id = 'file',
                              mode = file.get('@mode', None),
                              destname = file.get('@destname', None))

    if self.cvars['gpgsign-public-key']:
      # also include the gpg key in the config-rpm
      self.io.add_fpath(self.cvars['gpgsign-public-key'],
                        self.rpm.source_folder/'etc/pki/rpm-gpg')

    # add repos to cvars if necessary
    if self.config.get('updates/@repos', 'master') == 'all':
      self.DATA['variables'].append('cvars[\'repos\']')

  def generate(self):
    self._generate_repofile()
    if self.config.getbool('updates/@sync', True):
      self._include_sync_plugin()
    self.io.sync_input(cache=True)

  def _generate_repofile(self):
    repofile = ( self.rpm.source_folder/'etc/yum.repos.d/%s.repo' % self.name )

    lines = []

    # include a repo pointing to the published distribution
    if self.cvars['web-path'] is not None:
      lines.extend([ '[%s]' % self.name,
                     'name      = %s - %s' % (self.fullname, self.basearch),
                     'baseurl   = %s' % (self.cvars['web-path']/'os') ])
      # if we signed the rpms we use, include the gpgkey check in the repofile
      if self.cvars['gpgsign-public-key']:
        lines.extend(['gpgcheck = 1',
                      'gpgkey   = file://%s' % ('/etc/pki/rpm-gpg' /
                         self.cvars['gpgsign-public-key'].basename)])
      else:
        lines.append('gpgcheck = 0')
      lines.append('')

    # include repo(s) pointing to distribution inputs
    if self.config.get('updates/@repos', 'master') == 'all':
      for repo in self.cvars['repos'].values():
        try:
          if isinstance(repo.url.realm, pps.Path.rhn.RhnPath):
            continue
          lines.extend(repo.lines(pretty=True))
          lines.append('')
        except AttributeError:
          pass

    if len(lines) > 0:
      repofile.dirname.mkdirs()
      repofile.write_lines(lines)

      self.DATA['output'].append(repofile)

  def _include_sync_plugin(self):
    # replacement map for config file
    map = { 'masterrepo': self.name }

    # config
    configfile = self.rpm.source_folder/'etc/yum/pluginconf.d/sync.conf'
    configfile.dirname.mkdirs()
    # hackish - do %s replacement for masterrepo
    configfile.write_lines([ x % map for x in self.locals.L_YUM_PLUGIN['config'] ])

    # cronjob
    #cronfile = self.rpm.source_folder/'etc/cron.daily/sync.cron'
    #cronfile.dirname.mkdirs()
    #cronfile.write_lines(self.locals.L_YUM_PLUGIN['cron'])

    # plugin
    plugin = self.rpm.source_folder/'usr/lib/yum-plugins/sync.py'
    plugin.dirname.mkdirs()
    plugin.write_lines(self.locals.L_YUM_PLUGIN['plugin'])

  def get_pre(self):
    return self._make_script(self._process_script('pre'), 'pre')
  def get_post(self):
    scripts = [self._mk_post()]
    scripts.extend(self._process_script('post'))
    return self._make_script(scripts, 'post')
  def get_preun(self):
    return self._make_script(self._process_script('preun'), 'preun')
  def get_postun(self):
    scripts = self._process_script('postun')
    scripts.append(self._mk_postun())
    return self._make_script(scripts, 'postun')
  def get_verifyscript(self):
    return self._make_script(self._process_script('verifyscript'), 'verifyscript')

  def get_triggers(self):
    triggers = TriggerContainer()

    for elem in self.config.xpath('trigger', []):
      key   = elem.get('@package')
      id    = elem.get('@type')
      inter = elem.get('@interpreter', None)
      text  = elem.get('text()', None)

      if elem.get('@content', 'filename') == 'text':
        # if the content is 'text', write the string to a file and set
        # text to that value
        script = self.scriptdir/'triggerin-%s' % key
        if not text.endswith('\n'): text += '\n' # make sure it ends in a newline
        script.write_text(text)
        text = script

      flags = []
      if inter:
        flags.extend(['-p', inter])

      assert id in ['triggerin', 'triggerun', 'triggerpostun']
      t = Trigger(key)
      t[id+'_scripts'] = [text]
      if flags: t[id+'_flags'] = ' '.join(flags)
      triggers.append(t)

    return triggers

  def _mk_post(self):
    """Makes a post scriptlet that installs each <file> to the given
    destination, backing up any existing files to .rpmsave"""
    script = ''

    # move support files as needed
    sources = []
    for support_file in self.io.list_output('file'):
      src = '/' / support_file.relpathfrom(self.rpm.source_folder)
      dst = '/' / src.relpathfrom('/' / self.filerelpath)
      sources.append(dst)

    script += 'file="%s"' % '\n      '.join(sources)
    script += '\ns=%s\n' % ('/' / self.filerelpath)

    script += '\n'.join([
      '',
      'for f in $file; do',
      '  if [ -e $f ]; then',
      '    %{__mv} $f $f.rpmsave',
      '  fi',
      '  if [ ! -d `dirname $f` ]; then',
      '    %{__mkdir} -p `dirname $f`',
      '  fi',
      '  %{__mv} $s/$f $f',
      '  /sbin/restorecon $f',
      'done',
      '', ])

    return script

  def _mk_postun(self):
    """Makes a postun scriptlet that uninstalls each <file> and restores
    backups from .rpmsave, if present."""
    script = ''

    script += 'if [ "$1" == "0" ]; then\n'

    sources = []
    for support_file in self.io.list_output('file'):
      src = '/' / support_file.relpathfrom(self.rpm.source_folder)
      dst = '/' / src.relpathfrom('/' / self.filerelpath)

      sources.append(dst)

    script += '\n  file="%s"' % '\n        '.join(sources)

    script += '\n'.join([
        '',
        '  for f in $file; do',
        '    if [ -e $f.rpmsave ]; then',
        '      %{__mv} -f $f.rpmsave $f',
        '    else',
        '      %{__rm} -f $f',
        '    fi',
        '  done',
        '',
      ])
    script += '\nfi\n'

    return script

  def _process_script(self, script_type):
    """Returns a list of pps paths and strings; pps path items should be
    read to obtain script content, while strings should be interpreted as
    raw script content themselves (intended for use with _make_script(),
    below."""
    scripts = []

    for elem in self.config.xpath('script[@type="%s"]' % script_type, []):
      if elem.get('@content', 'filename') == 'text':
        scripts.append(elem.text)
      else:
        scripts.append(self.io.abspath(elem.text))

    return scripts

  def _make_script(self, iterable, id):

    """For each item in the iterable, if it is a pps path, read the file and
    concat it onto the script; otherwise, concat the string onto the script"""
    script = ''

    for item in iterable:
      if isinstance(item, pps.Path.BasePath):
        self.copy_callback.start(item, '')
        fsrc = item.open('rb')
        fdst = StringIO()
        self.copy_callback._cp_start(item.stat().st_size, item.basename)
        read = 0
        while True:
          buf = fsrc.read(16*1024)
          if not buf: break
          fdst.write(buf)
          read += len(buf)
          self.copy_callback._cp_update(read)
        self.copy_callback._cp_end(read)

        fdst.seek(0)
        script += fdst.read() + '\n'
      else:
        assert isinstance(item, basestring)
        script += item + '\n'

    if script:
      self.scriptdir.mkdirs()
      (self.scriptdir/id).write_text(script)
      return self.scriptdir/id
    else:
      return None
