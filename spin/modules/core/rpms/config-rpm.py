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
from rendition import pps

from spin.constants import BOOLEANS_TRUE
from spin.event     import Event
from spin.validate  import InvalidConfigError

from spin.modules.shared import RpmBuildMixin, Trigger, TriggerContainer

import md5

API_VERSION = 5.0

EVENTS = {'rpms': ['ConfigRpmEvent']}

class ConfigRpmEvent(RpmBuildMixin, Event):
  def __init__(self):
    Event.__init__(self,
      id = 'config-rpm',
      version = '0.93',
      provides = ['custom-rpms-data'],
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
      'variables': ['name', 'fullname', 'distroid', 'rpm.release'],
      'config':    ['.'],
      'input':     [],
      'output':    [self.rpm.build_folder],
    }

  def validate(self):
    for file in self.config.xpath('file', []):
      # if using raw output mode, a filename must be specified; otherwise,
      # we don't know what to name the file
      if file.get('@content', None) and not file.get('@filename', None):
        raise InvalidConfigError(self.config.getroot().file,
          "'raw' content type specified without accompying 'filename' "
          "attribute:\n %s" % file)

  def setup(self):
    self.rpm.setup_build()

    self.scriptdir.mkdirs()
    self.filedir.mkdirs()

    for file in self.config.xpath('file', []):
      text = file.text
      if file.get('@content', 'filename') == 'raw':
        # if the content is 'raw', write the raw string to a file and set
        # text to that value
        fn = self.filedir/file.get('@filename')
        if not fn.exists() or fn.md5sum() != md5.new(text).hexdigest():
          fn.write_text(text)
        text = fn

      self.io.add_fpath(text, ( self.rpm.build_folder //
                                self.filerelpath //
                                file.get('@dest',
                                         '/usr/share/%s/files' % self.name) ),
                              id = 'file',
                              mode = file.get('@mode', None))


    if self.cvars['gpgsign-public-key']:
      # also include the gpg key in the config-rpm
      self.io.add_fpath(self.cvars['gpgsign-public-key'],
                        self.rpm.build_folder/'etc/pkg/rpm-gpg')

  def generate(self):
    self._generate_repofile()
    self.io.sync_input(cache=True)

  def _generate_repofile(self):
    repofile = ( self.rpm.build_folder/'etc/yum.repos.d/%s.repo' % self.name )

    lines = []

    # include a repo pointing to the published distro
    if self.config.get('repofile/@distro', 'True') in BOOLEANS_TRUE:
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

    # include the given list of repoids, either a space separated list of
    # repoids or '*', which means all repoids, all from the <repos> section
    repoids = self.config.get('repofile/@repoids', '*').strip()
    if repoids:
      if repoids == '*':
        repoids = self.cvars['repos'].keys()
      else:
        repoids = repoids.split()

      for repoid in repoids:
        if repoid in self.cvars['repos']:
          lines.extend(self.cvars['repos'][repoid].lines(pretty=True))
          lines.append('')
        else:
          raise RuntimeError("Invalid repoid '%s'; valid repoids are %s"
                             % (repoid, self.cvars['repos'].keys()))

      self.DATA['variables'].append('cvars[\'repos\']')

    if len(lines) > 0:
      repofile.dirname.mkdirs()
      repofile.write_lines(lines)

      self.DATA['output'].append(repofile)

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

      if elem.get('@content', 'filename') == 'raw':
        # if the content is 'raw', write the raw string to a file and set
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
      src = '/' / support_file.relpathfrom(self.rpm.build_folder)
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

    script += 'if "$1" == "0"; then\n'

    sources = []
    for support_file in self.io.list_output('file'):
      src = '/' / support_file.relpathfrom(self.rpm.build_folder)
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
      if elem.get('@content', 'filename') == 'raw':
        scripts.append(elem.text)
      else:
        scripts.append(self._config.file.dirname / elem.text)

    return scripts

  def _make_script(self, iterable, id):

    """For each item in the iterable, if it is a pps path, read the file and
    concat it onto the script; otherwise, concat the string onto the script"""
    script = ''

    for item in iterable:
      if isinstance(item, pps.Path.BasePath):
        script += item.read_text() + '\n'
      else:
        assert isinstance(item, basestring)
        script += item + '\n'

    if script:
      self.scriptdir.mkdirs()
      (self.scriptdir/id).write_text(script)
      return self.scriptdir/id
    else:
      return None
