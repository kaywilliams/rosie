#
# Copyright (c) 2011
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

from systemstudio.util import pps
from systemstudio.util.repo import YumRepo

from systemstudio.event        import Event
from systemstudio.event.fileio import MissingXpathInputFileError
from systemstudio.validate     import InvalidConfigError

from systemstudio.modules.shared import RpmBuildMixin, Trigger, TriggerContainer
from systemstudio.errors         import assert_file_readable

import cPickle
import hashlib
import yum

class ConfigEventMixin(RpmBuildMixin):
  configxpath = '.' # path to config element

  def __init__(self): # call after creating self.DATA
    RpmBuildMixin.__init__(self,
      'system-config',
      "The system-config package provides scripts and supporting files for "
		  "configuring %s systems." % self.fullname,
      "%s configuration scripts and supporting files" % self.fullname,
      requires = ['coreutils', 'policycoreutils']
    )

  def validate(self):
    self.io.validate_destnames([ path for path in 
      self.config.xpath((self.configxpath + '/files'), [] ) ])

  def setup(self, webpath, files_cb=None, files_text="downloading files",
            **kwargs):
    self.webpath = webpath
    self.files_cb = files_cb
    self.files_text = files_text
    self.rpm.setup_build(**kwargs)

    self.scriptdir   = self.rpm.build_folder/'scripts'
    self.filerelpath = pps.path('usr/share/system-config/files')

    # add files for synchronization to the build folder
    self.io.add_xpath(self.configxpath + '/files', 
                      self.rpm.source_folder // self.filerelpath, 
                      destdir_fallback = 'usr/share/system-config/files', 
                      id = 'build-input')

    # add all scripts as input so if they change, we rerun
    for script in self.config.xpath(self.configxpath + '/script',  []) + \
                  self.config.xpath(self.configxpath + '/trigger', []):
      if script.get('@content', 'file') == 'file':
        assert_file_readable(script.text, 
                             xpath=self._configtree.getpath(script),
                             cls=MissingXpathInputFileError)
        self.DATA['input'].append(script.text)

    # compute input repos text and add to diff variables
    self.input_repos_text = []

    for repo in self.cvars['repos'].values(): #include input repos
      try:
        #  exclude rhn repos
        if isinstance(repo.url.realm, pps.Path.rhn.RhnPath):
          continue
        # exclude local file repos
        if "file:///" in repo.url:
          continue
        self.input_repos_text.extend(repo.lines(pretty=True))
        self.input_repos_text.append('')
      except AttributeError:
        pass

    self.DATA['variables'].append('input_repos_text')

    # setup gpgkeys
    self.cvars['gpgcheck-enabled'] = self.config.getbool(
                                     'updates/@gpgcheck', True)
    self.pklfile = self.mddir/'gpgkeys.pkl'
    self.gpgkey_dir = self.SOFTWARE_STORE/'gpgkeys'

    if not self.cvars['gpgcheck-enabled']:
      return

    for repo in (self.cvars['repos'].values() +
                 # using a dummy repo since rpmbuild repo not yet created
                 [YumRepo(id='dummy', gpgkey=self.cvars['pubkey'])]):
      for url in repo.gpgkey:
        self.io.add_fpath(url,
          self.gpgkey_dir,
          destname='RPM-GPG-KEY-%s' % \
            yum.YumBase()._retrievePublicKey(url, yum.yumRepo.YumRepository(
            str(repo)))[0]['hexkeyid'].lower(),
          id='gpgkeys')

  def run(self):
    for path in [ self.pklfile, self.gpgkey_dir ]:
      path.rm(recursive=True, force=True)
    RpmBuildMixin.run(self)

  def generate(self):
    self.io.process_files(cache=True, callback=self.files_cb, 
                          text=self.files_text, what='build-input')
    self.io.process_files(cache=True, callback=self.files_cb, 
                          text=self.files_text, what='gpgkeys')
    self._generate_files_checksums()
    self._generate_repofile()
    if self.config.getbool(self.configxpath + '/updates/@sync', True):
      self._include_sync_plugin()

  def _generate_files_checksums(self):
    """Creates a file containing checksums of all <files>. For use in 
    determining whether to backup existing files at install time."""
    md5file = ( self.rpm.source_folder/'usr/share/system-config/md5sums' )

    lines = []

    # compute checksums

    for file in (self.rpm.source_folder // self.filerelpath).findpaths(
                 type=pps.constants.TYPE_NOT_DIR):
      src = '/' / file.relpathfrom(self.rpm.source_folder)
      md5sum = file.checksum(type='md5')
      lines.append('%s %s' % (md5sum, src))

    md5file.dirname.mkdirs()
    md5file.write_lines(lines)

    self.DATA['output'].append(md5file)

  def _generate_repofile(self):
    repofile = ( self.rpm.source_folder/'etc/yum.repos.d/system.repo' )

    lines = []
    # include distribution repo
    if self.webpath is not None:
      baseurl = self.webpath
      lines.extend([ '[%s]' % self.name,
                     'name      = %s - %s' % (self.fullname, self.basearch),
                     'baseurl   = %s' % baseurl,
                     'metadata_expire = 0',
                     'gpgcheck = %s' % (self.cvars['gpgcheck-enabled']),
                     ])
      lines.append('gpgkey = %s' % ', '.join(self._gpgkeys()))

    # include input repos
    lines.append('') 
    lines.extend(self.input_repos_text)

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
    scripts = [self._mk_pre()]
    scripts.extend(self._process_script('pre'))
    return self._make_script(scripts, 'pre')
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

    for elem in self.config.xpath(self.configxpath + '/trigger', []):
      key   = elem.get('@package')
      id    = elem.get('@type')
      inter = elem.get('@interpreter', None)
      text  = elem.get('text()', None)

      if elem.get('@content', 'file') == 'text':
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

  def _mk_pre(self):
    """Makes a pre scriptlet that copies an existing md5sums file later use
    by the post scriptlet"""
    script = ''

    script += 'file=/usr/share/system-config/md5sums\n'

    script += '\n'.join([
      '',
      'if [ -e $file ]; then',
      '  /bin/cp $file $file.prev',
      'else',
      '  /bin/mkdir -p `dirname $file`',
      '  touch $file.prev',
      'fi',
      '', ])

    return script

  def _mk_post(self):
    """Makes a post scriptlet that installs each <file> to the given
    destination, backing up any existing files to .rpmsave"""
    script = ''

    # move support files as needed
    sources = []
    for support_file in (self.rpm.source_folder // self.filerelpath).findpaths(
                         type=pps.constants.TYPE_NOT_DIR):
      src = '/' / support_file.relpathfrom(self.rpm.source_folder)
      dst = '/' / src.relpathfrom('/' / self.filerelpath)
      sources.append(dst)

    script += 'file="%s"' % '\n      '.join(sources)
    script += '\nmd5file=/usr/share/system-config/md5sums\n'
    script += 'mkdirs=/usr/share/system-config/mkdirs\n'
    script += 's=%s\n' % ('/' / self.filerelpath)
    script += 'changed=""\n'

    script += '\n'.join([
      '',
      'for f in $file; do',
      '  # create .rpmsave and add file to changed variable, if needed',
      '  if [ -e $f ]; then',
      '    curr=`md5sum $f | sed -e "s/ .*//"`',
      '    new=`grep $f $md5file | sed -e "s/ .*//"`',
      '    prev=`grep $f $md5file.prev | sed -e "s/ .*//"`',
      '    if [[ $curr != $new ]]; then',
      '      if [[ $curr != $prev ]]; then',
      '        # file changed by user',
      '        /bin/mv $f $f.rpmsave',
      '        changed="$changed $f"',
      '      fi',
      '    fi',
      '  fi',
      '  # mkdirs one level at a time, if needed, and track for later removal',
      '  if [ ! -d `dirname $f` ]; then',
      '    levels="${f//[^\/]/}"',
      '    for i in `seq 2 ${#levels}`; do',
      '      dir=`echo $f | cut -f 1-$i -d/`',
      '      if [ ! -d $dir ]; then',
      '        /bin/mkdir $dir',
      '        echo $dir >> $mkdirs',
      '      fi',
      '    done',
      '  fi',
      '  # copy file to final location',   
      '  /bin/cp --preserve=all $s/$f $f',
      '  /sbin/restorecon $f',
      'done',
      '', ])

    script += '\nchanged=\"$changed `diff $md5file $md5file.prev | grep -o \'\/.*\' | sed s!$s!!g`\"\n'

    return script

  def _mk_postun(self):
    """Makes a postun scriptlet that uninstalls obsolete <files> and
    restores backups from .rpmsave, if present."""
    script = ''

    sources = []
    for support_file in (self.rpm.source_folder // self.filerelpath).findpaths(
                         type=pps.constants.TYPE_NOT_DIR):
      src = '/' / support_file.relpathfrom(self.rpm.source_folder)
      dst = '/' / src.relpathfrom('/' / self.filerelpath)

      sources.append(dst)

    script += 'file="%s"' % '\n      '.join(sources)
    script += '\ns=%s\n' % ('/' / self.filerelpath)
    script += 'mkdirs=/usr/share/system-config/mkdirs\n'

    script += '\n'.join([
        '',
        'for f in $file; do',
        '  if [ ! -e $s/$f ]; then',
        '    if [ -e $f.rpmsave ]; then',
        '      /bin/mv -f $f.rpmsave $f',
        '    else',
        '      /bin/rm -f $f',
        '    fi',
        '  fi',
        'done',
        '[[ -d $s ]] && find $s -depth -empty -type d -exec rmdir {} \;',
        'if [ -e $mkdirs ]; then',
        '  #first pass to remove empty dirs',
        '  for f in `cat $mkdirs`; do',
        '    if [ -e $f ] ; then',
        '      rmdir --ignore-fail-on-non-empty -p $f',
        '    fi',
        '  done',
        '  #second pass to remove dirs from mkdirs file',
        '  for f in `cat $mkdirs`; do',
        '    if [ ! -e $f ] ; then',
        '      sed -i s!$f\$!!g $mkdirs',
        '    fi',
        '  # third pass to remove empty lines from mkdirs',
        '  sed -i /$/d $mkdirs',
        '  done',
        'fi',
      ])

    # remove md5sums.prev file   
    script += '\n/bin/rm -f /usr/share/system-config/md5sums.prev\n'
    # remove mkdirs file on uninstall
    script += 'if [ $1 -eq 0 ]; then\n'
    script += '  rm -f $mkdirs\n'
    script += 'fi\n'

    return script

  def _process_script(self, script_type):
    """Returns a list of pps paths and strings; pps path items should be
    read to obtain script content, while strings should be interpreted as
    raw script content themselves (intended for use with _make_script(),
    below."""
    scripts = []
    for elem in self.config.xpath(self.configxpath + '/script[@type="%s"]' 
                                  % script_type, []):
      if elem.get('@content', 'file') == 'text':
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
      script = 'set -e \n' + script # force the script to fail at runtime if 
                                    # any item within it fails
      self.scriptdir.mkdirs()
      (self.scriptdir/id).write_text(script)
      return self.scriptdir/id
    else:
      return None

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
      self.cvars['gpgkeys']=cPickle.load(fo)
      fo.close()
    else:
      self.cvars['gpgkeys']=[]

