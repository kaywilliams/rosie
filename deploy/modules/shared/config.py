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
import copy 
import re

from deploy.errors   import (DeployEventError, MissingIdError,
                                   DuplicateIdsError)
from deploy.event    import Event, CLASS_META
from deploy.dlogging  import L0
from deploy.util     import pps

from deploy.modules.shared import (MkrpmRpmBuildMixin,
                                         ExecuteEventMixin,
                                         RepoSetupEventMixin,
                                         Trigger, 
                                         TriggerContainer)

from deploy.util.rxml.tree import MACRO_REGEX


def make_config_rpm_events(ptr, modname, element_name, globals):
  config_rpm_ids = getattr(ptr, 'cvars[\'config-rpm-ids\']', [])
  new_events = []
  xpath   = '/*/%s/%s' % (modname, element_name)

  # create event classes based on user configuration
  for config in ptr.definition.xpath(xpath, []):

    # convert user provided id to a valid class name
    rpmid = config.getxpath('@id', None)
    if rpmid == None: 
      raise MissingIdError(element=modname)
    name = re.sub('[^0-9a-zA-Z_]', '', rpmid).capitalize()
    setup_name = '%sConfigRpmSetupEvent' % name
    base_name = '%sConfigRpmEvent' % name

    # get config path and rpmid
    config_base = '%s[@id="%s"]' % (xpath, rpmid)

    # check for dups
    if rpmid in config_rpm_ids:
      raise DuplicateIdsError(element=element_name, id=rpmid)

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
    config_rpm_ids.append(rpmid)
    for name in [setup_name, base_name]:
      new_events.append(name)

  # update cvars rpm-event-ids
  ptr.cvars['config-rpm-ids'] = config_rpm_ids

  return new_events

class ConfigRpmSetupEventMixin(RepoSetupEventMixin, ExecuteEventMixin):

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
      'input':     [],
      'config':    [],
      'variables': [],
      'output':    [],
    }

    RepoSetupEventMixin.__init__(self)
    ExecuteEventMixin.__init__(self)

  def setup(self):
    # TODO make prep-scripts fit with our overall test-run-clean model?
    # TODO document
    for script in self.config.xpath('prep-script', []):
      file=self.mddir / 'prep-script' 
      file.write_text(script.text)
      file.chmod(0750)
      if script.getbool('@verbose', False):
        self.logger.log(1, L0(self.id))
      self._local_execute(file, verbose=script.getbool('@verbose', False))


class ConfigRpmEventMixin(MkrpmRpmBuildMixin): 
  config_mixin_version = "1.02"

  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-rpm' % self.rpmid,
      parentid = 'config-rpms',
      ptr = ptr,
      version = 1.00,
      provides = ['config-rpm'],
      config_base = self.config_base,
    )
 
    self.conditionally_requires.add('packages')
    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'input':     [],
      'config':    ['.'],
      'variables': [],
      'output':    [],
    }

    MkrpmRpmBuildMixin.__init__(self)

  def validate(self):
    self.io.validate_destnames([ path for path in 
      self.config.xpath(('files'), [] ) ])

    # rpmbuild behaves badly with unclosed macros in scripts, resulting in a
    # confusing error about installed but unpackaged files (which occurs
    # because rpmbuild fails to find the %files element)
    for elem in self.config.xpath('*[name()="script" or name()="trigger"]', []):
      text = copy.deepcopy(elem.text)
      count = 0 
      while True:
        inner_macros = re.findall(MACRO_REGEX, text)
        for macro in inner_macros:
          count += 1
          text = text.replace(macro, '', 1)
        if not inner_macros:
          break

      if not count == elem.text.count('%{'):
        message = ("ERROR: the following %s element contains a macro "
                   "placeholder with unbalanced braces '%%{}':\n\n%s"
                   % (elem.tag, elem))
        raise ConfigRpmEventError(message=message)

  def setup(self, **kwargs):
    self.DATA['variables'].append('config_mixin_version')

    name = self.config.getxpath('name/text()', self.rpmid)
    desc = self.config.getxpath('description/text()', 
       "The %s package provides configuration files and scripts for "
       "the %s repository." % (self.rpmid, self.fullname))
    summary = self.config.getxpath('summary/text()', name) 
    license = self.config.getxpath('license/text()', 'GPLv2')

    MkrpmRpmBuildMixin.setup(self, name=name, desc=desc, summary=summary, 
                             license=license, 
                             requires = ['coreutils', 'diffutils', 'findutils',
                                         'grep', 'sed'])

    self.libdir      = getattr(self, 'test_lib_dir', self.LIB_DIR)
    self.scriptdir   = self.build_folder/'scripts'
    self.rootinstdir = self.libdir / 'config' 
    self.installdir  = self.rootinstdir/name
    self.filerelpath = self.installdir/'files'
    self.srcfiledir  = self.source_folder // self.filerelpath
    self.md5file     = self.installdir/'md5sums'

    # resolve module macros
    self.resolve_macros(map={'%{rpmid}': name,
                                    '%{installdir}': self.installdir})

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
    self.debug_postfile = self.debugdir/'post-script'

  def run(self):
    MkrpmRpmBuildMixin.run(self)

  def apply(self):
    MkrpmRpmBuildMixin.apply(self)
    self.cvars.setdefault('config-rpms', []).append(self.rpminfo['name'])

  def generate(self):
    for what in ['files', 'triggers']:
      self.io.process_files(cache=True, what=what)

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

      # make the file executable
      file.chmod(0750)

      # link file to debug folder for installation by the rpm for 
      # easier user debugging
      self.link(file, self.debugdir/'%s-script' % file.basename)

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
      '  /bin/cp --preserve=mode,ownership,timestamps $s/$f $f',
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
      other=`find %(rootinstdir)s -name md5sums | grep -v %(md5file)s` || true

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
          /bin/mv -f $f.rpmsave $f
        else
          /bin/rm -f $f
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
      sed -i s!$f\$!!g $mkdirs
    fi
  # third pass to remove empty lines from mkdirs
  sed -i /$/d $mkdirs
  done
fi

# remove md5sums.prev file   
/bin/rm -f %(installdir)s/md5sums.prev

# remove per-system folder uninstall
if [ $1 -eq 0 ]; then
  rm -rf %(installdir)s
fi
""" % { 'files':        '\n      '.join(sources),
        'relpath':      '/' / self.filerelpath,
        'installdir':   self.installdir,
        'name':         self.rpm.name,
        'rootinstdir':  self.rootinstdir,
        'md5file':      self.md5file,
      }

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
      file =  self.debugdir/'%s-script' % script_type
      file.dirname.mkdirs()
      s = [ x.encode('utf8') for x in s ]
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
class ConfigRpmEventError(DeployEventError): 
  message = "%(message)s"


# -------- init methods called by new_rpm_events -------- #
def init_config_setup_event(self, ptr, *args, **kwargs):
  ConfigRpmSetupEventMixin.__init__(self, ptr, *args, **kwargs)

def init_config_event(self, ptr, *args, **kwargs):
  ConfigRpmEventMixin.__init__(self, ptr, *args, **kwargs)
