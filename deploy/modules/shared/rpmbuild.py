
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
from ConfigParser import ConfigParser
from UserDict import DictMixin

import copy 
import lxml
import pexpect 
import re
import rpmUtils

from deploy.util import mkrpm
from deploy.util import pps

from deploy.dlogging  import L1
from deploy.errors    import DeployEventError
from deploy.event     import Event

from deploy.util.rxml import config

from deploy.modules.shared import (ShelveMixin, CompsSetupEventMixin,
                                   ExecuteEventMixin, LocalExecute)

from deploy.util.difftest.filesdiff import ChecksumDiffTuple

RPM_EXT = {'rpm' : '.rpm',
           'srpm': '.src.rpm'}

__all__ = ['RpmBuildMixin', 'MkrpmRpmBuildMixin', 'RPM_EXT', 'Trigger', 
           'TriggerContainer', 'RpmNotFoundError'] 


class RpmBuildMixin(CompsSetupEventMixin, ShelveMixin, mkrpm.rpmsign.GpgMixin):
  """
  Base mixin for working with Deploy rpms. Handles signing rpms and caching
  rpm data. Currently used by rpm-downloading events including srpmbuild and 
  packages events. Also serves as a baseclass for deploy-created rpm (see
  MkrpmRpmBuildMixin).
  """
  rpmbuild_mixin_version = "1.03"

  def __init__(self):
    self.conditionally_requires.add('gpg-signing-keys')
    self.provides.update(['rpmbuild-data'])
    self.requires.update(['dist-tag'])
    self.rpms = [] # list of rpmbuild dicts (get_rpmbuild_data()) to be 
                   # managed by the mixin
    CompsSetupEventMixin.__init__(self)
    ShelveMixin.__init__(self)

  @property
  def rpm_paths(self):
    return [ x['rpm-path'] for x in self.rpms ]

  def setup(self):
    CompsSetupEventMixin.setup(self)

    self.DATA.setdefault('variables', set()).update(['rpmbuild_mixin_version'])

    self._setup_signing_keys()

  def run(self):
    self._sign_rpms()
    self._cache_rpmdata()

    self.DATA['output'].update(self.rpm_paths)

  def apply(self):
    self.local_rpmbuild_data = self.unshelve('rpmbuild_data', {})

    for k,v in self.local_rpmbuild_data.items():

      # restore absolute path to rpms
      path = self.METADATA_DIR / v['rpm-path']
      v['rpm-path'] = path

    self.cvars.setdefault('rpmbuild-data', {}).update(self.local_rpmbuild_data)

  def verify_rpms_exist(self):
    for rpm_path in self.rpm_paths:
      self.verifier.failUnlessExists(rpm_path)

  def _setup_rpm_from_path(self, path, dest, type):
    assert type in ['rpm', 'srpm']

    # get validarchs
    if type == 'rpm':  validarchs = self.validarchs
    if type == 'srpm': validarchs = ['src']

    # get list of matching rpms/srpms
    path = pps.path(path).abspath()
    paths = path.dirname.findpaths(
                           type=pps.constants.TYPE_NOT_DIR, 
                           mindepth=1, maxdepth=1,
                           regex=r'.*/%s.*%s' %
                           (path.basename.replace(RPM_EXT[type], ''),
                            RPM_EXT[type].replace('.', '\.')))

    # convert to a convenient structure for processing
    paths = [ (p, rpmUtils.miscutils.splitFilename(p.basename)) for p in paths ]

    # eliminate non-matching names and archs
    for p,tup in paths[:]:
      n,v,r,e,a = tup 
      if (path.basename in n and path.basename != n or 
          a not in validarchs):
        paths.remove((p,tup))

    # get current version (EVR)
    while len(paths) > 1:
      path1, tup1 = paths.pop()
      path2, tup2 = paths.pop()
      n1,v1,r1,e1,a1  = tup1
      n2,v2,r2,e2,a2  = tup2 

      # compare EVR
      result = rpmUtils.miscutils.compareEVR((e1,v1,r1),(e2,v2,r2))
      assert result in [-1, 0, 1]
      if result == -1: # path2 is newer, return it to the list
        paths.insert(0, (path2, tup2))
      elif result == 0: # versions are the same
        # keep the best arch
        for arch in validarchs:
          if a1 == arch:
            paths.insert(0, (path1, tup1))
            break 
          elif a2 == arch:
            paths.insert(0, (path2, tup2))
            break
      elif result == 1: # path1 is newer
        paths.insert(0, (path1, tup2))
        
    if not paths:
      raise RpmNotFoundError(name=path.basename, dir=path.dirname, type=type)

    self.io.add_fpath(paths[0][0], dest, id=type)

  def _get_rpmbuild_data(self, rpmpath,
                         packagereq_type='mandatory', 
                         packagereq_default=None, 
                         packagereq_requires=None):

      data = {}
      data['rpm-path']  = pps.path(rpmpath)
  
      # set attrs used in comps file
      data['packagereq-default']  = packagereq_default
      data['packagereq-requires'] = packagereq_requires
      data['packagereq-type']     = packagereq_type
 
      # read metadata from rpm to handle both config-rpm and srpmbuild cases
      info = rpmUtils.miscutils.splitFilename(rpmpath.basename)
  
      data['rpm-name']      = str(info[0])
      data['rpm-version']   = str(info[1])
      data['rpm-release']   = str(info[2])
      data['rpm-arch']      = str(info[4])

      # requires used to lock package versions in depsolve
      # obsoletes used to remove pkgs from comps
      ts = rpmUtils.transaction.initReadOnlyTransaction()
      hdr = rpmUtils.miscutils.hdrFromPackage(ts, rpmpath)
      data['rpm-requires']  = [ x.DNEVR()[2:] 
                              for x in hdr.dsFromHeader('requirename') ]
      data['rpm-obsoletes'] = [ x.DNEVR()[2:] 
                              for x in hdr.dsFromHeader('obsoletename') ]
      del ts
      del hdr

      return data

  def _setup_signing_keys(self):
    if 'gpg-signing-keys' in self.cvars:
      self.gpgsign = self.cvars['gpg-signing-keys'] # convenience variable
      self.pubtext = self.gpgsign['pubkey'].read_text().rstrip()
      self.sectext = self.gpgsign['seckey'].read_text().rstrip()
      self.DATA['variables'].update(['pubtext', 'sectext', 
                                     'gpgsign[\'passphrase\']'])

  def _sign_rpms(self):
    if self.rpms and 'gpg-signing-keys' in self.cvars:
      self.log(4, L1("signing rpm(s)"))

      # set up homedir - used for signing
      homedir = self.mddir / 'gnupg'
      homedir.rm(recursive=True, force=True)
      homedir.mkdirs(mode=0700)
      homedir.chown(0,0)

      for key in [self.gpgsign['pubkey'], self.gpgsign['seckey']]:
        self.import_key(homedir, key)

      for rpm_path in self.rpm_paths:
        # sign rpm
        self.log(4, L1("%s" % rpm_path.basename))
        command = ('/bin/rpm --resign %s ' 
                   '--define="_signature gpg" '
                   '--define="_gpg_path %s" '
                   '--define="_gpg_name %s" '
                   '--define="_gpgbin /usr/bin/gpg"'
                   % (rpm_path, homedir, self.get_gpgname(homedir)))

        try:
          child = pexpect.spawn(command)
          child.expect('Enter pass phrase:')
          child.sendline(self.gpgsign['passphrase'])
          child.expect(pexpect.EOF)

        except Exception, e:
          message = ("Unable to sign rpm '%s'. The error message was '%s'"
                      % (rpm_path, str(e)))
          raise RpmBuildError(message=message)

        child.close()

        if child.exitstatus != 0:
          message = ("Unable to sign rpm '%s'. The error message was '%s'"
                     % (rpm_path, child.before))
          raise RpmBuildError(message=message)

  def _cache_rpmdata(self):
    rpmbuild_data = {}
    if self.rpms:
      for item in copy.deepcopy(self.rpms):
         rpmbuild_data[item['rpm-name']] = item

         # store relative path to rpm
         path=item['rpm-path'].relpathfrom(self.METADATA_DIR)
         rpmbuild_data[item['rpm-name']]['rpm-path'] = path
    self.shelve('rpmbuild_data', rpmbuild_data)


class MkrpmRpmBuildMixin(ExecuteEventMixin, RpmBuildMixin):
  """
  Mixin for creating rpms from scratch using util.mkrpm, e.g. for use by
  config-rpm and release-rpm
  """
  mkrpmbuild_mixin_version = "1.01"

  def __init__(self, *args, **kwargs):
    RpmBuildMixin.__init__(self)
    ExecuteEventMixin.__init__(self)

  def setup(self, name=None, version=None, arch=None, desc=None,
            summary=None, license=None, author=None, email=None,
            requires=None, provides=None, obsoletes=None, force_release=None,
            rpmconf=None):

    RpmBuildMixin.setup(self) # deals with gpg signing
    ExecuteEventMixin.setup(self)

    self.dist = '.%s%s' % (self.cvars['dist-tag'], self.version)

    # container for info that should be tracked in variables
    # release should not go here since it is incremented in run
    self.rpminfo = dict(
      name = name,
      version = version or self.version,
      arch = arch or 'noarch',
      desc = desc,
      summary = summary,
      author  = author,
      email = email,
      license = license or 'GPLv2',
      requires = requires or [],
      provides = provides or [],
      obsoletes = obsoletes or [],
      )

    if rpmconf is not None:
      self.rpmconf = rpmconf
    else:
      self.rpmconf = self.config
    self.rpminfo['obsoletes'].extend(self.rpmconf.xpath('obsoletes/text()', []))
    self.rpminfo['provides'].extend([ x for x in self.rpminfo['obsoletes']])
    self.rpminfo['provides'].extend(self.rpmconf.xpath('provides/text()', []))
    self.rpminfo['requires'].extend(self.rpmconf.xpath('requires/text()', []))
    self.DATA.setdefault('variables', set()).update(['mkrpmbuild_mixin_version'])

    self.force_release = force_release
    self.build_folder  = self.mddir / 'build'
    self.source_folder = self.build_folder / 'source'

    self.diff.setup(self.DATA)
    # use checksums to better handle runtime-generated files (e.g. by 
    # prep-scripts)
    self.diff.input.tupcls = ChecksumDiffTuple

    self.DATA.setdefault('variables', set()).update(
                         ['mkrpmbuild_mixin_version', 
                          'rpminfo', 'force_release'])

    # common variables for user file inclusion
    self.localdir    = getattr(self, 'test_local_dir', self.LOCAL_ROOT)
    self.scriptdir   = self.build_folder/'scripts'
    self.configdir   = self.localdir/'config' 
    self.installdir  = self.configdir/self.rpminfo['name']
    self.filerelpath = self.installdir/'files'
    self.srcfiledir  = self.source_folder // self.filerelpath
    self.md5file     = self.installdir/'md5sums'

    self.cvars.setdefault('config-dir', self.configdir)

    self.DATA['variables'].add('localdir')

    # resolve module macros
    self.local_execute_obj = LocalExecute(self) 
    self.resolve_macros(
         map={'%{rpm-id}': self.rpminfo['name'],
              '%{install-dir}': self.installdir,
              '%{script-dir}': self.local_execute_obj.scriptdir,
              '%{script-data-dir}': self.local_execute_obj.datadir
              })

    # execute prep-scripts in setup (i.e. on every run), allowing output to
    # be used reliably in file and script elems by this and other config-rpms

    for script in self.rpmconf.xpath('prep-script', []):
      file=self.mddir / 'prep-script' 
      file.write_text(script.text)
      file.chmod(0750)
      # print the run message early if scripts are set to verbose
      if script.getbool('@verbose', False):
        self.logger.log(1, L0(self.id))
        self.suppress_run_message = True
      self._local_execute(file, script_id='prep-script', 
                          verbose=script.getbool('@verbose', False))

    # copies of user-provided scripts and triggers go here for easier 
    # user debugging
    self.debugdir    = self.source_folder // self.installdir
    self.debug_postfile = self.debugdir/'post'

  def run(self):
    release = self._get_release()

    # create build object
    self.rpm = RpmBuildObject(self, release+self.dist, 
                              copy.deepcopy(self.rpminfo))
    R = self.rpm

    for path in [ self.build_folder, R.rpm_path, R.srpm_path ]:
      path.rm(recursive=True, force=True)
    self.build_folder.mkdirs()
    self.generate()
    R.write_spec()
    R.write_manifest()

    self.log(1, L1("building %s-%s-%s.%s.rpm" % \
                   (R.name, R.version, R.release, R.arch)))

    try:
      mkrpm.build(R.build_folder, self.mddir, createrepo=False,
                  bdist_base=R.bdist_base, rpm_base=R.rpm_base,
                  dist_dir=R.dist_dir, keep_source=True,
                  quiet=(int(self.logger.threshold) < 5))
    except mkrpm.rpmbuild.RpmBuilderException, e:
      raise RpmBuildFailedException(message=str(e))

    self._save_release(release)
    self.DATA['output'].add(self.rpm.build_folder)

    self.rpms = [ self._get_rpmbuild_data(R.rpm_path) ]
    RpmBuildMixin.run(self)

  def apply(self):
    RpmBuildMixin.apply(self)

    # update user_required_packages
    group = self.rpmconf.getxpath('group/text()', self.default_groupid) 
    for r in self.local_rpmbuild_data:
      self.user_required_packages[r] = group

  def _get_release(self):
    if self.force_release: # use provided release
      return str(self.force_release).replace(self.dist, '')

    else: # bump calculated release  
      self.datfile = self.parse_datfile()
      release = self.datfile.getxpath('/*/%s/release/text()' %
                                (self.id), '0')
      return str(int(release)+1)

  def _save_release(self, release):
    root = self.parse_datfile()
    uElement = config.uElement
    parent   = uElement(self.id, parent=root)
    child    = uElement('release', parent=parent, text=release)
    self.write_datfile(root)

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

    for elem in self.rpmconf.xpath('trigger', []):
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
    for elem in self.rpmconf.xpath('script[@type="%s"]'
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


  # ----------- OPTIONAL METHODS --------#
  # determine what files are ghost
  def get_ghost_files(self): return None

  # rpm scripts
  def get_build(self):        return None
  def get_clean(self):        return None
  def get_install(self):      return None
  def get_prep(self):         return None
  def get_verifyscript(self): return None

  # trigger scripts
  def get_triggers(self):     return None


class RpmBuildObject:
  def __init__(self, ptr, release, rpminfo):
    self.ptr     = ptr
    self.release = release 
    self.name    = rpminfo['name']
    self.version = rpminfo['version']
    self.arch    = rpminfo['arch']
    self.desc    = rpminfo['desc']
    self.summary = rpminfo['summary']
    self.license = rpminfo['license']
    self.author  = rpminfo['author']

    self.obsoletes = rpminfo['obsoletes']
    self.requires  = rpminfo['requires']
    self.provides  = rpminfo['provides']

    # RPM build variables
    self.build_folder  = ptr.build_folder
    self.source_folder = ptr.source_folder 
    self.bdist_base    = self.build_folder / 'rpm-base'
    self.rpm_base      = self.build_folder / 'rpm'
    self.dist_dir      = self.build_folder / 'dist'

  #------------- PROPERTIES --------------#
  @property
  def rpm_path(self):
    return self.ptr.mddir/'RPMS/%s-%s-%s.%s.rpm' % \
             (self.name, self.version, self.release, self.arch)

  @property
  def srpm_path(self):
    return self.ptr.mddir/'SRPMS/%s-%s-%s.src.rpm' % \
           (self.name, self.version, self.release)

  @property
  def data_files(self):
    data_files = {}
    for item in self.source_folder.findpaths(type=pps.constants.TYPE_DIR,
                                             mindepth=1):
      files = item.findpaths(type=pps.constants.TYPE_NOT_DIR,
                             mindepth=1, maxdepth=1)
      if files:
        data_files.setdefault('/' / item.relpathfrom(self.source_folder), []).extend(files)
    return data_files

  #--------- RPM BUILD HELPER METHODS ---------#


  def write_spec(self):
    setupcfg = self.build_folder/'setup.cfg'

    spec = ConfigParser()

    # metadata section
    M = 'metadata'
    spec.add_section(M)

    spec.set(M, 'name',             self.name)
    spec.set(M, 'long_description', self.desc)
    spec.set(M, 'description',      self.summary)
    spec.set(M, 'author',           self.author)
    spec.set(M, 'version',          self.version)

    if self.license: spec.set(M, 'license', self.license)

    # bdist_rpm section
    B = 'bdist_rpm'
    spec.add_section(B)

    spec.set(B, 'force_arch',        self.arch)
    spec.set(B, 'distribution_name', self.name)
    spec.set(B, 'release',           self.release)

    if self.provides:  spec.set(B, 'provides',  ' '.join(self.provides))
    if self.requires:  spec.set(B, 'requires',  ' '.join(self.requires))
    if self.obsoletes: spec.set(B, 'obsoletes', ' '.join(self.obsoletes))

    # get the various script types
    build     = self.ptr.get_build()
    clean     = self.ptr.get_clean()
    install   = self.ptr.get_install()
    post      = self.ptr.get_post()
    posttrans = self.ptr.get_posttrans()
    postun    = self.ptr.get_postun()
    pre       = self.ptr.get_pre()
    prep      = self.ptr.get_prep()
    pretrans  = self.ptr.get_pretrans()
    preun     = self.ptr.get_preun()
    verify    = self.ptr.get_verifyscript()

    triggers = self.ptr.get_triggers()

    ghost = self.ptr.get_ghost_files()

    # add to bdist_rpm
    if build:     spec.set(B, 'build_script',   build)
    if clean:     spec.set(B, 'clean_script',   clean)
    if install:   spec.set(B, 'install_script', install)
    if post:      spec.set(B, 'post_install',   post)
    if posttrans: spec.set(B, 'post_trans',     posttrans)
    if postun:    spec.set(B, 'post_uninstall', postun)
    if pre:       spec.set(B, 'pre_install',    pre)
    if prep:      spec.set(B, 'prep_script',    prep)
    if pretrans:  spec.set(B, 'pre_trans',      pretrans)
    if preun:     spec.set(B, 'pre_uninstall',  preun)
    if verify:    spec.set(B, 'verify_script',  verify)

    if triggers:
      trigcfg = self.build_folder / 'triggers.cfg'
      triggers.write_config(trigcfg)
      spec.set(B, 'trigger_configs', trigcfg)

    if ghost: spec.set(B, 'ghost_files', '\n\t'.join(ghost))

    # distribution related data
    D = 'distribution'
    spec.add_section(D)

    self.add_data_files(spec, D)
    #self.add_config_files(spec, B) #config-rpm manages independently
    self.add_doc_files(spec, B)

    f = open(setupcfg, 'w')
    spec.write(f)
    f.close()

  def write_manifest(self):
    manifest = ['setup.py', 'setup.cfg']
    manifest.extend( [ x.relpathfrom(self.build_folder) for x in
                       self.source_folder.findpaths(
                         type=pps.constants.TYPE_NOT_DIR) ])
    (self.build_folder/'MANIFEST').write_lines(manifest)

  def add_data_files(self, spec, section):
    data = []
    for dir, files in self.data_files.items():
      data.append('\t%s : %s' % (dir, ', '.join(files)))
    if data: spec.set(section, 'data_files', '\n'.join(data))

  def add_config_files(self, spec, section):
    cfg = []
    for dir,files in self.data_files.items():
      if dir.startswith('/etc'): # config files
        cfg.extend([ dir/x.basename for x in files ])
    if cfg: spec.set(section, 'config_files', '\n\t'.join(cfg))

  def add_doc_files(self, spec, section):
    doc = []
    if (self.source_folder / 'COPYING').exists():
      doc.append('COPYING')
    for dir,files in self.data_files.items():
      if dir.startswith('/usr/share/doc'):
        doc.extend([ dir/x.basename for x in files ])
    if doc: spec.set(section, 'doc_files', '\n\t'.join(doc))

class TriggerContainer(list):
  def __init__(self, iterable=None):
    iterable = iterable or []
    self.check(iterable)
    list.__init__(self, iterable)

  def write_config(self, file):
    lines = []
    for trigger in self:
      lines.append(str(trigger))
      lines.append('')
    lines = [ x.encode('utf8') for x in lines ]
    file.write_lines(lines)

  def extend(self, item):
    self.check(item)
    list.extend(self, item)

  def append(self, item):
    self.check(item)
    list.append(self, item)

  def insert(self, index, item):
    self.check(item)
    list.insert(self, index, item)

  def check(self, item):
    if not hasattr(item, '__iter__'):
      item = [item]
    if isinstance(item, Trigger):
      return
    for x in item:
      if not isinstance(x, Trigger):
        raise TypeError("Trying to add non-Trigger object '%s' to TriggerContainer" % x)


class Trigger(dict):
  def __init__(self, id, **kwargs):
    self.id = id
    dict.__init__(self, **kwargs)

  def __str__(self):
    lines = ['[%s]' % self.id]
    if 'triggerid' not in self:
      lines.append('triggerid = %s' % self.id)
    for key, value in self.iteritems():
      if hasattr(value, '__iter__'):
        val = '\n\t'.join(value)
        lines.append('%s = %s' % (key, val.strip('\n')))
      else:
        lines.append('%s = %s' % (key, value))
    return '\n'.join(lines)

class RpmNotFoundError(DeployEventError):
  def __init__(self, name, dir, type):
    self.name = name
    self.dir = dir
    self.type = type

  def __str__(self):
    return "No %s '%s' found at '%s'\n" % (self.type, self.name, self.dir)

class RpmBuildError(DeployEventError):
  message="%(message)s"

class RpmBuildFailedException(RpmBuildError):
  message = "RPM build failed.  See build output below for details:\n%(message)s"


