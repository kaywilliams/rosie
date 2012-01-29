#
# Copyright (c) 2012
# CentOS Solutions Foundation. All rights reserved.
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

from centosstudio.util  import pps
from centosstudio.event import Event

from centosstudio.modules.shared import (RpmBuildMixin, 
                                          Trigger, 
                                          TriggerContainer)

class ConfigRpmEventMixin(RpmBuildMixin):
  config_mixin_version = "1.21"

  def __init__(self, rpmxpath=None): # call after creating self.DATA
    self.conditionally_requires.add('packages')
    self.rpmxpath = rpmxpath or '.'

    RpmBuildMixin.__init__(self,
      '%s-config' % self.name,   
      "The %s-config package provides scripts and files for configuring " 
      "packages from the %s repository." % (self.name, self.fullname),
      "%s configuration" % self.fullname,
      requires = ['coreutils']
    )

  def validate(self):
    self.io.validate_destnames([ path for path in 
      self.config.xpath((self.rpmxpath + '/files'), [] ) ])

  def setup(self, files_cb=None, files_text="downloading files",
            **kwargs):
    self.DATA['variables'].append('config_mixin_version')
    self.DATA['config'].append(self.rpmxpath)

    self.masterrepo = '%s-%s' % (self.name, 
                      hashlib.md5(self.solutionid).hexdigest()[-6:])
    self.files_cb = files_cb
    self.files_text = files_text

    RpmBuildMixin.setup(self, **kwargs)

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

  def run(self):
    RpmBuildMixin.run(self)

  def generate(self):
    for what in ['files', 'triggers']:
      self.io.process_files(cache=True, callback=self.files_cb, 
                            text=self.files_text, what=what)

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

  def apply(self):
    self.rpm._apply()
