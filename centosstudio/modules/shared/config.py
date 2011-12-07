#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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

from centosstudio.util import pps
from centosstudio.util.repo import YumRepo

from centosstudio.event        import Event
from centosstudio.event.fileio import MissingXpathInputFileError 
from centosstudio.validate     import InvalidConfigError

from centosstudio.modules.shared import (RpmBuildMixin, 
                                          Trigger, 
                                          TriggerContainer)
from centosstudio.errors         import (assert_file_readable, 
                                          CentOSStudioError)

import cPickle
import hashlib
import yum

class ConfigEventMixin(RpmBuildMixin):
  config_mixin_version = "1.21"

  def __init__(self, rpmxpath=None): # call after creating self.DATA
    self.conditionally_requires.add('packages')
    self.rpmxpath = rpmxpath or '.'

    RpmBuildMixin.__init__(self,
      'system-config-centosstudio-%s' % self.name,   
      "The system-config-centosstudio-%s package provides scripts and files " 
      "for configuring %s systems." % (self.name, self.fullname),
      "%s system configuration" % self.fullname,
      requires = ['coreutils']
    )

  def validate(self):
    self.io.validate_destnames([ path for path in 
      self.config.xpath((self.rpmxpath + '/files'), [] ) ])

  def setup(self, webpath, files_cb=None, files_text="downloading files",
            **kwargs):
    self.DATA['variables'].append('config_mixin_version')
    self.DATA['config'].append(self.rpmxpath)

    self.webpath = webpath
    self.masterrepo = '%s-%s' % (self.name, 
                      hashlib.md5(self.systemid).hexdigest()[-6:])
    self.files_cb = files_cb
    self.files_text = files_text

    RpmBuildMixin.setup(self, **kwargs)
    self.rpm.requires.extend(self.add_requires())

    self.scriptdir   = self.rpm.build_folder/'scripts'
    self.rootinstdir = pps.path('/etc/sysconfig/centosstudio')
    self.installdir  = self.rootinstdir/self.name
    self.filerelpath = self.installdir/'files'
    self.srcfiledir  = self.rpm.source_folder // self.filerelpath
    self.md5file     = self.installdir/'md5sums'

    # add files for synchronization to the build folder
    self.io.add_xpath('files', self.srcfiledir, 
                      destdir_fallback = self.filerelpath, 
                      id = 'files')

    # add triggers for synchronization to scripts folder
    for script in self.config.xpath('%s/trigger' % self.rpmxpath, []):
      self.io.add_xpath(self._configtree.getpath(script),
                        self.scriptdir, destname='%s-%s' % (
                        script.get('@type'), script.get('@trigger')), 
                        content='text',
                        id='triggers')

    # copies of user-provided scripts and triggers go here for easier 
    # user debugging
    self.debugdir    = self.rpm.source_folder // self.installdir
    self.debug_postfile = self.debugdir/'config-post-script'

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

    self.DATA['variables'].extend(['input_repos_text', 'masterrepo', 'webpath'])

    # setup gpgkeys
    self.cvars['gpgcheck-enabled'] = self.config.getbool(
                                     '%s/updates/@gpgcheck' % self.rpmxpath,
                                     True)
    self.pklfile = self.mddir/'gpgkeys.pkl'
    self.gpgkey_dir = self.SOFTWARE_STORE/'gpgkeys'

    if not self.cvars['gpgcheck-enabled']:
      return

    for repo in (self.cvars['repos'].values() +
                 # using a dummy repo since rpmbuild repo not yet created
                 [YumRepo(id='dummy', gpgkey=self.cvars['pubkey'])]):
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

  def add_requires(self):
    self.extra_requires = [ p for p in self.cvars['comps-object'].all_packages 
                 if p.startswith('system-config-centosstudio-') ]
    self.DATA['variables'].append('extra_requires')             
    return self.extra_requires

  def generate(self):
    for what in ['files', 'gpgkeys', 'triggers']:
      self.io.process_files(cache=True, callback=self.files_cb, 
                            text=self.files_text, what=what)

    self._generate_repofile()
    if self.config.getbool('%s/updates/@sync' % self.rpmxpath, True):
      self.rpm.requires.append('yum')
      self._include_sync_plugin()
    self._generate_files_checksums()
    self.files =  [ x[len(self.srcfiledir):] 
                    for x in self.srcfiledir.findpaths(
                    type=pps.constants.TYPE_NOT_DIR, mindepth=1 )]

  def _generate_files_checksums(self):
    """Creates a file containing checksums of all <files>. For use in 
    determining whether to backup existing files at install time."""
    md5file =  self.rpm.source_folder // self.md5file 

    lines = []

    # compute checksums
    strip = len(self.srcfiledir)

    for file in self.srcfiledir.findpaths(type=pps.constants.TYPE_NOT_DIR):
      md5sum = file.checksum(type='md5')
      lines.append('%s %s' % (md5sum, file[strip:]))

    md5file.dirname.mkdirs()
    md5file.write_lines(lines)
    md5file.chmod(0640)

    self.DATA['output'].append(md5file)

  def _generate_repofile(self):
    repofile = ( self.srcfiledir / 'etc/yum.repos.d/%s.repo' % self.name )

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

    # include input repos
    lines.append('') 
    lines.extend(self.input_repos_text)

    if len(lines) > 0:
      repofile.dirname.mkdirs()
      repofile.write_lines(lines)

      self.DATA['output'].append(repofile)

  def _include_sync_plugin(self):
    # replacement map for config file
    map = { 'masterrepo': self.masterrepo }

    # config
    configfile = (self.srcfiledir / 'etc/yum/pluginconf.d/sync.conf')
    configfile.dirname.mkdirs()
    # hackish - do %s replacement for masterrepo
    configfile.write_lines([ x % map for x in self.locals.L_YUM_PLUGIN['config'] ])

    # cronjob
    #cronfile = (self.srcfiledir / 'etc/cron.daily/sync.cron')
    #cronfile.dirname.mkdirs()
    #cronfile.write_lines(self.locals.L_YUM_PLUGIN['cron'])

    # plugin
    plugin = (self.srcfiledir / 'usr/lib/yum-plugins/sync.py')
    plugin.dirname.mkdirs()
    plugin.write_lines(self.locals.L_YUM_PLUGIN['plugin'])

  def get_pre(self):
    scripts = [self._mk_pre()]
    scripts.extend(self._process_script('pre'))
    return self._make_script(scripts, 'pre')
  def get_post(self):
    scripts = [self._mk_post()]
    scripts.extend(self._process_script('post'))
    scripts.append('/bin/chmod 750 %s' % self.installdir)
    scripts.append('trap - INT TERM EXIT')
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

    triggers.append(self._mk_triggerin())

    for elem in self.config.xpath('%s/trigger' % self.rpmxpath, []):
      key   = elem.get('@trigger')
      id    = elem.get('@type')
      inter = elem.get('@interpreter', None)
      file  = self.scriptdir/'%s-%s' % (elem.get('@type'), elem.get('@trigger'))

      flags = []
      if inter:
        flags.extend(['-p', inter])

      # create trigger objects
      assert id in ['triggerin', 'triggerun', 'triggerpostun']
      t = Trigger(key)
      t[id+'_scripts'] = [file]
      if flags: t[id+'_flags'] = ' '.join(flags)
      triggers.append(t)

      # add 'set -e' to bash trigger scripts for consistent behavior with
      # non-trigger scripts
      if inter is None or 'bash' in inter:
        file.write_text('set -e\n' + file.read_text())

      # make the file executable
      file.chmod(0750)

      # link file to debug folder for installation by the rpm for 
      # easier user debugging
      self.link(file, self.debugdir/'config-%s-script' % file.basename)

    return triggers

  def _mk_pre(self):
    """Makes a pre scriptlet that copies an existing md5sums file later use
    by the post scriptlet"""
    script = ''

    script += 'file=%s\n' % self.md5file

    script += '\n'.join([
      '',
      'if [ -e $file ]; then',
      '  /bin/cp $file $file.prev',
      'else',
      '  if [ ! -e $file.prev ]; then',
      '  /bin/mkdir -p `dirname $file`',
      '  touch $file.prev',
      '  fi',
      'fi',
      '', ])

    return script

  def _mk_post(self):
    """Makes a post scriptlet that installs each <file> to the given
    destination, backing up any existing files to .rpmsave"""
    script = ''

    # move support files as needed
    script += 'files="%s"' % '\n      '.join(self.files)
    script += '\nmd5file=%s\n' % self.md5file
    script += 'mkdirs=%s/mkdirs\n' % self.installdir
    script += 's=%s\n' % self.filerelpath
    script += 'changed=""\n'

    script += '\n'.join([
      '',
      'for f in $files; do',
      '  # create .rpmsave and add file to changed variable, if needed',
      '  if [ -e $f ]; then',
      '    curr=`md5sum $f | sed -e "s/ .*//"`',
      '    new=`grep " $f$" $md5file | sed -e "s/ .*//"`',
      '    prev=`grep " $f$" $md5file.prev | sed -e "s/ .*//"`',
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
      'done',
      '', ])

    # add differences between current and previous md5sum files to changed
    # variable; yuck lots of massaging to get a space separated list 
    script += '\n'
    script += 'changed=\"$changed `diff $md5file $md5file.prev | grep -o \'\/.*\' | sed -e \"s|$s||g\" | tr \'\\n\' \' \'`\"\n'
    script += '\n'

    file = self.debug_postfile[len(self.rpm.source_folder):]

    script += '# add changed variable to user debugging script\n'
    script += 'if [[ -e %s ]]; then sed -i "/set -e/ a\\\n' % file
    script += 'changed=\'$changed\'" %s\n' % file
    script += 'fi\n'
    script += '\n'
    script += '# remove md5sum file if script fails\n'
    script += 'trap "rm -f $md5file" INT TERM EXIT\n'
    script += '\n'
    script += '\n#------ Start of User Scripts ------#\n'
    return script

  def _mk_postun(self):
    """Makes a postun scriptlet that uninstalls obsolete <files> and
    restores backups from .rpmsave, if present."""
    script = ''

    sources = []
    for support_file in self.srcfiledir.findpaths(
                        type=pps.constants.TYPE_NOT_DIR):
      src = '/' / support_file.relpathfrom(self.rpm.source_folder)
      dst = '/' / src.relpathfrom('/' / self.filerelpath)

      sources.append(dst)

    script += 'files="%s"' % '\n      '.join(sources)
    script += '\ns=%s\n' % ('/' / self.filerelpath)
    script += 'mkdirs=%s/mkdirs\n' % self.installdir

    script += '\n'.join([
        '',
        'for f in $files; do',
        '  if [ ! -e $s/$f ]; then', #file missing from source folder
        '    if [ -e $f ]; then',    #file exists on disk
        '      remove="true"',
        '      for md5file in `find %s -name md5sums | grep -v %s`' % ( 
               self.rootinstdir, self.md5file),
        '      do',
        '        while read line; do',
        '          row=($line)',
        '          if [[ ${row[1]} == $f ]]; then', #file listed in other rpm
        '            remove="false"',
        '          fi',
        '        done < $md5file',
        '      done',
        '      if [[ $remove == true ]]; then',
        '        if [ -e $f.rpmsave ]; then',
        '          /bin/mv -f $f.rpmsave $f',
        '        else',
        '          /bin/rm -f $f',
        '        fi',
        '      fi',
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
    script += '\n/bin/rm -f %s/md5sums.prev\n' % self.installdir
    # remove per-system folder uninstall
    script += 'if [ $1 -eq 0 ]; then\n'
    script += '  rm -rf %s\n' % self.installdir
    script += 'fi\n'

    return script

  def _mk_triggerin(self):
    # reset selinux context for installed files
    key = 'selinux-policy-targeted'
    type = 'triggerin'
    file = self.scriptdir/'%s-%s' % (type, key)
    lines = [
    'set -e',
    'files="%s"' % '\n      '.join(self.files),
    '',
    'for f in $files; do',
    '  /sbin/restorecon $f',
    'done',]

    file.write_text('\n'.join(lines))
    file.chmod(0750)

    t = Trigger('selinux-policy-targeted')
    t[type+'_scripts'] = [file]

    return t 

  def _process_script(self, script_type):
    """Processes and returns user-provided scripts for a given script type. 
    Also, saves these to a file which is included in the rpm and installed
    to client machines for debugging purposes."""
    scripts = []
    for elem in self.config.xpath('%s/script[@type="%s"]' 
                                   % (self.rpmxpath, script_type), []):
      scripts.append(elem.text)

    if scripts:
      #write file for inclusion in rpm for end user debugging
      s = scripts[:]
      s.insert(0, 'set -e\n')
      file =  self.debugdir/'config-%s-script' % script_type
      file.dirname.mkdirs()
      file.write_lines(s)
      file.chmod(0750)
      self.DATA['output'].append(file)

    return scripts

  def _make_script(self, iterable, id):

    """For each item in the iterable concat it onto the script. Write the
    completed script to a file for inclusion in the rpm spec file."""
    script = ''

    for item in iterable:
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

class MissingGPGKeyError(CentOSStudioError):
  message = "Cannot find GPG key specified for the '%(repo)s' package repository: '%(file)s'"
