#
# Copyright (c) 2015
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
import copy 
import re

from deploy.errors   import (DeployEventError, MissingIdError,
                             DuplicateIdsError, ConfigError)
from deploy.event    import Event, CLASS_META
from deploy.dlogging import L0
from deploy.util     import pps

from deploy.modules.shared import (MkrpmRpmBuildMixin,
                                         ExecuteEventMixin,
                                         LocalExecute,
                                         RepoSetupEventMixin,
                                         Trigger, 
                                         TriggerContainer)

from deploy.util.difftest.filesdiff import ChecksumDiffTuple
from deploy.util.rxml.tree import MACRO_REGEX


def make_config_rpm_events(ptr, modname, element_name, globals):
  config_rpm_elems = getattr(ptr, 'cvars[\'config-rpm-elems\']', {})
  new_events = []
  xpath   = '/*/%s/%s' % (modname, element_name)

  # create event classes based on user configuration
  for config in ptr.definition.xpath(xpath, []):

    # convert user provided id to a valid class name
    rpmid = config.getxpath('@id', None)
    if rpmid == None: 
      raise MissingIdError(config)
    name = re.sub('[^0-9a-zA-Z_]', '', rpmid).capitalize()
    setup_name = '%sConfigRpmSetupEvent' % name
    base_name = '%sConfigRpmEvent' % name

    # get config path and rpmid
    config_base = '%s[@id="%s"]' % (xpath, rpmid)

    # check for dups
    if rpmid in config_rpm_elems:
      if config == config_rpm_elems[rpmid]:
        continue # elem exactly matches a previous elem, ignore
      else:
        raise DuplicateIdsError(ptr.definition.xpath('%s[@id="%s"]'
                                                      % (xpath, rpmid)))

    # create new classes
    exec """%s = config.ConfigRpmSetupEvent('%s', 
                         (config.ConfigRpmSetupEventMixin,), 
                         { 'rpmid'      : '%s',
                           'config_base': '%s',
                           '__init__'   : config.init_config_setup_event,
                         }
                        )""" % (
                        setup_name, setup_name, rpmid, config_base) in globals

    exec """%s = config.ConfigRpmEvent('%s', 
                         (config.ConfigRpmEventMixin,), 
                         { 'rpmid'      : '%s',
                           'config_base': '%s',
                           '__init__'   : config.init_config_event,
                         }
                        )""" % (
                        base_name, base_name, rpmid, config_base) in globals

    # update lists with new classname
    config_rpm_elems[rpmid] = config 
    for name in [setup_name, base_name]:
      new_events.append(name)

  # update cvars rpm-event-ids
  ptr.cvars['config-rpm-elems'] = config_rpm_elems

  return new_events

class ConfigRpmSetupEventMixin(RepoSetupEventMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-rpm-setup' % self.rpmid,
      parentid = 'config-rpms-setup',
      ptr = ptr,
      version = 1.00,
      provides = ['config-rpm-setup'],
      config_base = self.config_base,
      suppress_run_message = True,
    )

    self.DATA = {
      'input':     set(),
      'config':    set(),
      'variables': set(),
      'output':    set(),
    }

    RepoSetupEventMixin.__init__(self)


class ConfigRpmEventMixin(ExecuteEventMixin, MkrpmRpmBuildMixin): 
  config_mixin_version = "1.05"

  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-rpm' % self.rpmid,
      parentid = 'config-rpms',
      ptr = ptr,
      version = 1.00,
      provides = ['config-rpm'],
      config_base = self.config_base,
    )
 
    # Add rpm requires, provides and obsoletes to event. This allows event
    # ordering to mimic rpm ordering. Needed for prep scripts (in 
    # ConfigRpmSetupEventMixin) to provide content for use for later rpms, and
    # may as well have setup and main events follow the same order.
    self.conditionally_requires.update(
      ['%s-rpm' % x for x in self.config.xpath('./requires/text()', [])])
    self.provides.update(
      ['%s-rpm' % x for x in self.config.xpath('./provides/text()', [])])
    self.provides.update(
      ['%s-rpm' % x for x in self.config.xpath('./obsoletes/text()', [])])

    self.conditionally_requires.add('packages')
    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'input':     set(),
      'config':    set(['.']),
      'variables': set(),
      'output':    set(),
    }

    ExecuteEventMixin.__init__(self)
    MkrpmRpmBuildMixin.__init__(self)

  def validate(self):
    self.io.validate_destnames([ path for path in 
      self.config.xpath(('files'), [] ) ])

    for elem in self.config.xpath('*[name()="script" or name()="trigger"]', []):
      text = copy.deepcopy(elem.text)

      # error on empty content
      if not text:
        raise EmptyScriptContentError(elem)

      # rpmbuild behaves badly with unclosed macros in scripts, resulting in a
      # confusing error about installed but unpackaged files (which occurs
      # because rpmbuild fails to find the %files element)
      count = 0 
      while True:
        inner_macros = re.findall(MACRO_REGEX, text)
        for macro in inner_macros:
          count += 1
          text = text.replace(macro, '', 1)
        if not inner_macros:
          break

      if not count == elem.text.count('%{'):
        raise InvalidMacroError(elem)

  def setup(self, **kwargs):
    self.diff.setup(self.DATA)

    # use checksums to better handle runtime-generated files (e.g. by 
    # prep-scripts)
    self.diff.input.tupcls = ChecksumDiffTuple

    self.DATA['variables'].add('config_mixin_version')

    ExecuteEventMixin.setup(self)

    desc = self.config.getxpath('description/text()', 
       "The %s package provides configuration files and scripts for "
       "the %s repository." % (self.rpmid, self.fullname))
    summary = self.config.getxpath('summary/text()', self.rpmid) 
    license = self.config.getxpath('license/text()', 'GPLv2')

    MkrpmRpmBuildMixin.setup(self, name=self.rpmid, desc=desc, summary=summary, 
                             license=license, 
                             requires = ['coreutils', 'diffutils', 'findutils',
                                         'grep', 'sed'])

    self.localdir    = getattr(self, 'test_local_dir', self.LOCAL_ROOT)
    self.scriptdir   = self.build_folder/'scripts'
    self.configdir   = self.localdir/'config' 
    self.installdir  = self.configdir/self.rpmid
    self.filerelpath = self.installdir/'files'
    self.srcfiledir  = self.source_folder // self.filerelpath
    self.md5file     = self.installdir/'md5sums'

    self.cvars.setdefault('config-dir', self.configdir)

    self.DATA['variables'].add('localdir')

    # resolve module macros
    self.local_execute_obj = LocalExecute(self) 
    self.resolve_macros(
         map={'%{rpm-id}': self.rpmid,
              '%{install-dir}': self.installdir,
              '%{script-dir}': self.local_execute_obj.scriptdir,
              '%{script-data-dir}': self.local_execute_obj.datadir
              })

    # execute prep-scripts in setup (i.e. on every run), allowing output to
    # be used reliably in file and script elems by this and other config-rpms
    for script in self.config.xpath('prep-script', []):
      file=self.mddir / 'prep-script' 
      file.write_text(script.text)
      file.chmod(0750)
      # print the run message early if scripts are set to verbose
      if script.getbool('@verbose', False):
        self.logger.log(1, L0(self.id))
        self.suppress_run_message = True
      self._local_execute(file, script_id='prep-script', 
                          verbose=script.getbool('@verbose', False))

    # add files for synchronization to the build folder
    self.io.add_xpath('files', self.srcfiledir, allow_text=True) 

    # add triggers for synchronization to scripts folder
    for script in self.config.xpath('trigger', []):
      self.io.add_xpath(self._config.getroottree().getpath(script),
                        self.scriptdir, destname='%s-%s' % (
                        script.getxpath('@type'), script.getxpath('@trigger')),
                        content='text', allow_text=True,
                        id='triggers')

    # copies of user-provided scripts and triggers go here for easier 
    # user debugging
    self.debugdir    = self.source_folder // self.installdir
    self.debug_postfile = self.debugdir/'post'

  def run(self):
    MkrpmRpmBuildMixin.run(self)

  def apply(self):
    MkrpmRpmBuildMixin.apply(self)
    self.cvars.setdefault('config-rpms', []).append(self.rpminfo['name'])

  def generate(self):
    for what in ['files', 'triggers']:
      self.io.process_files(cache=True, callback=self.link_callback,
                            text=None, what=what)

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
    md5file.chmod(0600)

    self.DATA['output'].add(md5file)

  def get_pretrans(self):
    return self._make_script(self._process_script('pretrans'), 'pretrans')
  def get_pre(self):
    scripts = [self._mk_pre()]
    scripts.extend(self._process_script('pre'))
    return self._make_script(scripts, 'pre')
  def get_post(self):
    scripts = [self._mk_post()]
    scripts.extend(self._process_script('post'))
    scripts.append('chmod 700 %s' % self.installdir)
    scripts.append('trap - INT TERM EXIT')
    return self._make_script(scripts, 'post')
  def get_preun(self):
    return self._make_script(self._process_script('preun'), 'preun')
  def get_postun(self):
    scripts = [self._mk_postun()]
    scripts.extend(self._process_script('postun'))
    return self._make_script(scripts, 'postun')
  def get_posttrans(self):
    scripts = [self._mk_posttrans()]
    scripts.extend(self._process_script('posttrans'))
    return self._make_script(scripts, 'posttrans')

  def get_triggers(self):
    triggers = TriggerContainer()

    for elem in self.config.xpath('trigger', []):
      key   = elem.getxpath('@trigger')
      id    = elem.getxpath('@type')
      inter = elem.getxpath('@interpreter', None)
      file  = self.scriptdir/'%s-%s' % (elem.getxpath('@type'), elem.getxpath('@trigger'))

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
      # regular scripts
      if inter is None or inter in ['/bin/bash', 'bin/sh']:
        text = 'set -e\n'
        file.write_text(text + file.read_text())

      # ensure an interpreter line in non-shell scripts so rpmbuild doesn't
      # get confused when auto-adding requires and think things like import 
      # statements are shell commands
      if inter is not None:
        if not file.read_lines()[0].startswith('#!'):
          file.write_text('#!%s\n' % inter + file.read_text())

      # make the file executable
      file.chmod(0750)

      # link file to debug folder for installation by the rpm for 
      # easier user debugging
      self.link(file, self.debugdir/'%s' % file.basename)

    return triggers

  def _mk_pre(self):
    """Makes a pre scriptlet that copies an existing md5sums file later use
    by the post scriptlet"""
    script = ''

    script += 'file=%s\n' % self.md5file
    script += '\n'.join([
      '',
      'if [ -e $file ]; then',
      '  cp $file $file.prev',
      'else',
      '  if [ ! -e $file.prev ]; then',
      '  for d in %s %s %s; do' % (self.localdir, self.configdir,
                                   self.installdir),
      '    [[ -d $d ]] || mkdir $d',
      '    chmod 700 $d',
      '    chown root:root $d',
      '  done',
      '  touch $file.prev',
      '  chmod 600 $file.prev',
      '  chown root:root $file.prev',
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
      '        mv $f $f.rpmsave',
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
      '        mkdir $dir',
      '        echo $dir >> $mkdirs',
      '      fi',
      '    done',
      '  fi',
      '  # copy file to final location',
      '  cp --preserve=mode,ownership,timestamps $s/$f $f',
      'done',
      '', ])

    # add differences between current and previous md5sum files to changed
    # variable; yuck lots of massaging to get a space separated list 
    script += '\n'
    script += ('changed=\"$changed `diff $md5file $md5file.prev | '
               'grep -o \'\/.*\' | '
               'sed -e \"s|^$s||g\" | tr \'\\n\' \' \'`\"\n')
    script += '\n'

    file = self.debug_postfile[len(self.rpm.source_folder):]

    script += '# add changed variable to user debugging script\n'
    script += 'if [[ -e %s ]]; then sed -i "/set -e/ a\\\n' % file
    script += 'changed=\'$changed\'" %s\n' % file
    script += 'fi\n'
    script += '\n'
    script += '\n#------ Start of User Scripts ------#\n'
    return script

  def _mk_postun(self):
    """Makes a postun scriptlet that uninstalls obsolete <files> and
    restores backups from .rpmsave, if present."""

    sources = []
    for support_file in self.srcfiledir.findpaths(
                        type=pps.constants.TYPE_NOT_DIR):
      src = '/' / support_file.relpathfrom(self.rpm.source_folder)
      dst = '/' / src.relpathfrom('/' / self.filerelpath)

      sources.append(dst)

    script = """
files="%(files)s"
s=%(relpath)s
mkdirs=%(installdir)s/mkdirs
for f in $files; do
  if [ ! -e $s/$f ]; then # file missing from source folder
    if [ -e $f ]; then    #file exists on disk

      # find md5file for the current version of this rpm
      new=''
      if rpm -q %(name)s --quiet; then
        for file in `rpm -ql %(name)s`; do
          if [[ `basename $file` == md5sums ]] && [ -e $file ] ; then
            new=$file
          fi
        done
      fi

      # find md5files for other deploy managed rpms
      other=`find %(configdir)s -name md5sums | grep -v %(md5file)s` || true

      # process files
      md5files="$new $other"
      remove="true"
      for md5file in $md5files 
      do
        while read line; do
          row=($line)
          if [[ ${row[1]} == $f ]]; then #file in new or other rpm
            remove="false"
          fi
        done < $md5file
      done
      if [[ $remove == true ]]; then
        if [ -e $f.rpmsave ]; then
          mv -f $f.rpmsave $f
        else
          rm -f $f
        fi
      fi
    fi
  fi
done
[[ -d $s ]] && find $s -depth -empty -type d -exec rmdir {} \;
if [ -e $mkdirs ]; then
  #first pass to remove empty dirs
  for f in `cat $mkdirs`; do
    if [ -e $f ] ; then
      rmdir --ignore-fail-on-non-empty -p $f
    fi
  done
  #second pass to remove dirs from mkdirs file
  for f in `cat $mkdirs`; do
    if [ ! -e $f ] ; then
      sed -i "\|^$f$|d" $mkdirs
    fi
  done
fi

# remove md5sums.prev file   
rm -f %(installdir)s/md5sums.prev

# remove per-system folder uninstall
if [ $1 -eq 0 ]; then
  rm -rf %(installdir)s
fi
""" % { 'files':        '\n      '.join(sources),
        'relpath':      '/' / self.filerelpath,
        'installdir':   self.installdir,
        'name':         self.rpm.name,
        'configdir':    self.configdir,
        'md5file':      self.md5file,
      }

    return script

  def _mk_posttrans(self):
    # TODO - remove in the future once legacy clients are likely updated
    script = """
legacy_dir=/var/lib/deploy-client
legacy_conf_dir=$legacy_dir/config/%s

if [[ -d $legacy_conf_dir ]]; then
  # remove config-specific legacy dir
  rm -rf $legacy_conf_dir

  # remove parent legacy dir, if it contains only subfolders
  if ! find $legacy_dir -type f -print -quit | grep -q . ; then
    rm -rf $legacy_dir
  fi
fi
""" % self.installdir.basename

    return script

  def _process_script(self, script_type):
    """Processes and returns user-provided scripts for a given script type. 
    Also, saves these to a file which is included in the rpm and installed
    to client machines for debugging purposes."""
    scripts = []
    for elem in self.config.xpath('script[@type="%s"]'
                                   % script_type, []):
      scripts.append(elem.text)
    if scripts:
      #write file for inclusion in rpm for end user debugging
      s = scripts[:]
      s.insert(0, 'set -e\n')
      s.insert(0, '#!/bin/bash\n')
      file =  self.debugdir/'%s' % script_type
      file.dirname.mkdirs()
      s = [ x.encode('utf8') for x in s ]
      file.write_lines(s)
      file.chmod(0700)
      self.DATA['output'].add(file)

    return scripts

  def _make_script(self, iterable, id):
    """For each item in the iterable concat it onto the script. Write the
    completed script to a file for inclusion in the rpm spec file."""
    script = ''

    for item in iterable:
      assert isinstance(item, basestring)
      script += item + '\n'

    if script:
      set = 'set -e \n' # force the script to fail at runtime if 
                        # any item within it fails
      script = set + script 
      self.scriptdir.mkdirs()
      (self.scriptdir/id).write_text(script.encode('utf8'))
      return self.scriptdir/id
    else:
      return None

# ------ Metaclass for creating Config RPM Events -------- #
class ConfigRpmSetupEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)

class ConfigRpmEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)


# -------- Error Classes --------#
class EmptyScriptContentError(ConfigError):
  def __init__(self, elem):
    ConfigError.__init__(self, elem)

  def __str__(self):
    return ("Validation Error: the following element has no content:\n%s"
            % self.errstr)

class InvalidMacroError(ConfigError):
  def __init__(self, elem):
    ConfigError.__init__(self, elem, full=True)

  def __str__(self):
    return ("Validation Error: the following element contains a macro "
            "placeholder with unbalanced braces '%%{}':\n%s"
            % self.errstr)

# -------- init methods called by new_rpm_events -------- #
def init_config_setup_event(self, ptr, *args, **kwargs):
  ConfigRpmSetupEventMixin.__init__(self, ptr, *args, **kwargs)

def init_config_event(self, ptr, *args, **kwargs):
  ConfigRpmEventMixin.__init__(self, ptr, *args, **kwargs)
