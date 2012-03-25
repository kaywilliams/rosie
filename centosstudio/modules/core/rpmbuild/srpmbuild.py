#
# Copyright (c) 2011
# CentOS Solutions, Inc. All rights reserved.
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
import lxml
import optparse
import paramiko 
import re
import rpm
import rpmUtils
import signal
import yum

from centosstudio.callback     import TimerCallback
from centosstudio.cslogging    import MSG_MAXWIDTH, L0, L1, L2
from centosstudio.errors       import (CentOSStudioError,
                                       CentOSStudioEventError)
from centosstudio.event        import Event
from centosstudio.main         import Build
from centosstudio.util         import magic 
from centosstudio.util         import pps 
from centosstudio.util         import rxml 
from centosstudio.util         import sshlib 
from centosstudio.validate     import check_dup_ids

from centosstudio.util.pps.constants import TYPE_NOT_DIR


from centosstudio.modules.shared import (DeployEventMixin, SSHConnectCallback,
                                         ShelveMixin, RpmBuildMixin) 

from fnmatch import fnmatch

YUMCONF = '''
[main]
cachedir=/
persistdir=/
logfile=/depsolve.log
gpgcheck=0
reposdir=/
exclude=*debuginfo*

[%s]
name = Source RPM Repo
baseurl = %s
'''


class SrpmBuildMixinEvent(RpmBuildMixin, DeployEventMixin, ShelveMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-srpm' % self.srpmid, 
      parentid = 'rpmbuild',
      ptr = ptr,
      version = 1.03,
      config_base = '/*/%s/srpm[@id=\'%s\']' % (self.moduleid, self.srpmid),
    )
  
    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'input':     [],
      'config':    ['.'],
      'variables': [],
      'output':    [],
    }
  
    self.srpmfile = ''
    self.srpmdir  = self.mddir / 'srpm'

    self.rpmsdir   = self.mddir / 'rpms'

    self.datdir   = self.LIB_DIR / 'srpms'
    self.datdir.mkdirs()

    if self.version == "5":
      self.build_dir = pps.path('/usr/src/redhat')
    else:
      self.build_dir = pps.path('/root/rpmbuild')

    self.originals_dir = self.build_dir / 'originals'

    ShelveMixin.__init__(self)
    RpmBuildMixin.__init__(self)
  
  def setup(self):
    self.diff.setup(self.DATA)
    RpmBuildMixin.setup(self)
  
    # resolve macros
    srpmlast = self.unshelve('srpmlast', '')
    macros = {'%{srpm-id}': self.srpmid,
              '%{srpm-dir}': self.srpmdir,
              '%{srpm-last}': srpmlast,
              '%{rpms-dir}': self.rpmsdir,
             }
    self.config.resolve_macros('.', macros)
  
    # get srpm
    path = pps.path(self.config.get('path/text()', ''))
    repo = pps.path(self.config.get('repo/text()', ''))
    script = self.config.get('script/text()', '')
    if path: self._get_srpm_from_path(path)
    elif repo: self._get_srpm_from_repo(repo)
    elif script: self._get_srpm_from_script(script)

    # get base build machine definition
    search_dirs = self.SHARE_DIRS
    search_dirs.insert(0, self.mainconfig.file.dirname)
    default = ''
    for d in search_dirs:
      results = d.findpaths(mindepth=1, type=pps.constants.TYPE_NOT_DIR,
                            glob='%s-%s-%s.definition' % 
                            (self.moduleid, self.version, self.userarch))
      if results:
        default = results[0]
        break

    self.definition = self.config.get('definition/text()', 
                      self.config.get('/*/%s/definition/text()' % self.moduleid,
                      default))
    self.io.validate_input_file(self.definition)
    self.DATA['input'].append(self.definition)

  def run(self):
    # process srpm
    self._process_srpm()

    # update definition
    definition = self._update_definition()

    # start with a clean rpmsdir
    self.rpmsdir.rm(recursive=True, force=True)
    self.rpmsdir.mkdirs()

    # initialize builder
    try:
      builder = SrpmBuild(definition, self._get_build_machine_options(), [])
    except CentOSStudioError, e:
      raise BuildMachineCreationError(
              definition='based on \'%s\'' % self.definition, 
              error=e, idstr='', sep = MSG_MAXWIDTH * '=',)

    # build rpms
    if self.logger.threshold > 2:
      self.logger.log_header(3, "building '%s' SRPM" % self.srpmid)
    else:
      self.logger.log(2, L2("building '%s'" % self.srpmid))

    try:
      builder.main()
    except CentOSStudioError, e:
      raise BuildMachineCreationError(
                    definition='based on \'%s\'' % self.definition, 
                    error=e, idstr="--> build machine id: %s\n" %
                    builder.repoid, sep = MSG_MAXWIDTH * '=')

    self.logger.log(3, L0("%s" % '=' * MSG_MAXWIDTH))
    self.logger.log(3, L0(''))
   
    self.copy = self.config.getbool('@copy', True)
    self.shutdown = self.config.getbool('@shutdown', False)

    if self.copy or self.shutdown:
      params = dict( 
        hostname = builder.cvars['publish-setup-options']['hostname'],
        password = builder.cvars['publish-setup-options']['password'],
        username = 'root',
        port     = 22,)

      try:
        client = self._ssh_connect(params, log_format="L1") 
        if self.copy: self._copy_results(client)
        if self.shutdown:
          self._ssh_execute(client, 'poweroff', log_format="L1")

      finally:
        if 'client' in locals(): client.close()

    # verify rpms
    self.logger.log(3, L1("verifying rpms"))
    if hasattr(self, 'test_verify_rpms'): # set by test module
      badfile = self.rpmsdir / 'badfile'
      badfile.write_text('')

    rpmfiles = self.rpmsdir.findpaths(mindepth=1)
    for file in rpmfiles:
      if magic.match(file) != magic.FILE_TYPE_RPM:
        message = ("The file at '%s' does not appear to be an rpm." % file)
        raise SrpmBuildEventError(message=message)

    # use RpmBuildMixin to sign rpms, cache rpmdata, and add rpms as output
    self.rpms = [ self._get_rpmbuild_data(f) for f in rpmfiles ]
    RpmBuildMixin.run(self)

  def _get_srpm_from_path(self, path):
    if path.endswith('.src.rpm'): # add the file
      if not path.exists(): 
        raise SrpmNotFoundError(name=self.srpmid, path=path)
      self.io.add_fpath(path, self.srpmdir, id='srpm') 
    else: # add the most current matching srpm
      paths = path.findpaths(type=TYPE_NOT_DIR, mindepth=1, maxdepth=1, 
                             glob='%s*' % self.srpmid)
      if not paths: 
        raise SrpmNotFoundError(name=self.srpmid, path=path)
      while len(paths) > 1:
        path1 = paths.pop()
        path2 = paths.pop()
        _,v1,r1,e1,_  = rpmUtils.miscutils.splitFilename(path1.basename)
        _,v2,r2,e2,_  = rpmUtils.miscutils.splitFilename(path2.basename)
        result = rpmUtils.miscutils.compareEVR((e1,v1,r1),(e2,v2,r2))
        if result < 1: # path2 is newer, return it to the list
          paths.insert(0, path2)
        else: # path1 is newer, or they are the same
          paths.insert(0, path1)

      self.io.add_fpath(paths[0], self.srpmdir, id='srpm')

  def _get_srpm_from_repo(self, repo):
    yumdir = self.mddir / 'yum'
    yumdir.mkdirs()
    yumconf = yumdir / 'yum.conf'
    yumconf.write_text(YUMCONF % (self.id, repo))
    yb = yum.YumBase()
    yb.preconf.fn = fn=str(yumconf)
    yb.preconf.root = str(yumdir)
    yb.preconf.init_plugins = False
    yb.preconf.errorlevel = 0
    yb.doRpmDBSetup()
    yb.conf.cache = 0
    yb.doRepoSetup(self.id)
  
    try:
      yb.doSackSetup(archlist=['src'], thisrepo=self.id)
    except yum.Errors.RepoError:
      raise InvalidRepoError(url=repo)
  
    try:
      srpm = (yb.repos.getRepo(self.id).getPackageSack()
              .returnNewestByName(name=self.srpmid)[0])
    except yum.Errors.PackageSackError:
      raise SrpmNotFoundError(name=self.srpmid, path=repo)
      
    self.io.add_fpath(srpm.remote_url, self.srpmdir, id='srpm')
    del yb; yb = None

  def _get_srpm_from_script(self, script):
    # start with a clean srpmdir
    self.srpmdir.rm(recursive=True, force=True) 
    self.srpmdir.mkdirs()
  
    script_file = self.mddir / 'script'
    script_file.write_text(self.config.get('script/text()'))
    script_file.chmod(0750)
  
    self._local_execute(script_file)
  
    results = self.srpmdir.findpaths(glob='%s-*.src.rpm' % self.srpmid, 
                                      maxdepth=1)
  
    if not results:
      message = ("The script provided for the '%s' srpm did not output an "
                 "srpm beginning with '%s' and ending with '.src.rpm' in the "
                 "location specified by the %%{srpmdir} macro. See the "
                 "CentOS Studio documentation for information on using the "
                 "srpm/script element." % (self.srpmid, self.srpmid))
      raise SrpmBuildEventError(message=message)
    elif len(results) > 1:
      message = "more than one result: %s" % results
      raise SrpmBuildEventError(message=message)
    else:
      self.srpmfile = results[0]
      self.DATA['input'].append(self.srpmfile)

  def _process_srpm(self):
    self.io.process_files(cache=True)
    if self.srpmfile: # srpm provided by script
      self.DATA['output'].append(self.srpmfile)
    else: # srpm provided by path or repo
      self.srpmfile = self.io.list_output(what='srpm')[0]

    self.shelve('srpmlast', self.srpmfile.basename)

  def _update_definition(self):
    name, spec, requires = self._get_srpm_info(self.srpmfile)

    root = rxml.config.parse(self.definition).getroot()

    name =    self.moduleid
    version = self.version
    arch =    self.userarch

    # provide meaningful filename since it is also used for the .dat file
    root.file = self.datdir / '%s-%s-%s.definition' % (name, version, arch)

    # add main element
    if root.find('main') is not None: 
      root.remove(root.find('main'))

    main = rxml.config.Element('main')
    rxml.config.Element('name',    text=name, parent=main)
    rxml.config.Element('version', text=version, parent=main)
    rxml.config.Element('arch',    text=arch, parent=main)

    root.append(main)

    # add config-rpm for srpm requires
    config = root.get('/*/config-rpms', rxml.config.Element('config-rpms'))
    rpm = rxml.config.Element('rpm', parent=config, 
                              attrs={'id': '%s' % self.srpmid})
    child = rxml.config.Element('files', parent=rpm)
    child.set('destdir', self.originals_dir)
    child.text = self.srpmfile

    for req in requires:
      child = rxml.config.Element('requires', parent=rpm)
      child.text = req

    if root.find('config') is None:
      root.append(config)

    # use gpgsign from parent definition, if provided
    parent_gpgsign = copy.deepcopy(self.config.get('/*/gpgsign', None))
    child_gpgsign = root.get('/*/gpgsign', None)
    if parent_gpgsign is not None and child_gpgsign is None:
      root.append(parent_gpgsign)
     
    # append repos from parent definition, if provided
    parent_repos = copy.deepcopy(self.config.get('/*/repos', None))
    child_repos = root.get('/*/repos', None)
    if parent_repos is not None and child_repos is None:
      root.append(parent_repos)
    if parent_repos is not None and child_repos is not None:
      for repo in parent_repos.xpath('repo'):
        child_repo = child_repos.get("repo[@id='%s']" % repo.attrib['id'], None)
        if child_repo is not None: child_repos.remove(child_repo)
        child_repos.append(repo)

    #resolve macros
    root.resolve_macros('.', {
      '%{build-dir}': self.build_dir,
      '%{srpm}':      self.originals_dir / self.srpmfile.basename,
      '%{spec}':      self.build_dir / 'SPECS' / spec, })

    return root

  def _get_srpm_info(self, srpm):
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    hdr = rpmUtils.miscutils.hdrFromPackage(ts, srpm)
    name = hdr[rpm.RPMTAG_NAME]
    spec = [ f for f in hdr['FILENAMES'] if '.spec' in f ][0]
    requires = [ r.DNEVR()[2:] for r in hdr.dsFromHeader('requirename') ]
    del ts
    del hdr
    return (name, spec, requires) 

  def _get_build_machine_options(self):
    parser = optparse.OptionParser()
    parser.set_defaults(**dict(
      logthresh = self.logger.threshold,
      logfile   = self.options.logfile,
      libpath   = self.options.libpath,
      sharepath = self.options.sharepath,
      force_modules = [],
      skip_modules  = [],
      force_events  = ['deploy'],
      skip_events   = [],
      mainconfigpath = self.options.mainconfigpath,
      enabled_modules  = [],
      disabled_modules = [],
      list_modules = False,
      list_events = False,
      no_validate = False,
      validate_only = False,
      clear_cache = False,
      debug = self.options.debug,))

    opts, _ = parser.parse_args([])
    
    return opts

  def _copy_results(self, client):
    try:
      # copy files
      sftp = paramiko.SFTPClient.from_transport(client.get_transport())
      rpms = set()
      for dir in sftp.listdir(str(self.build_dir/'RPMS')):
        for file in sftp.listdir(str(self.build_dir/'RPMS'/dir)):
          if file.endswith('.rpm'):
            rpms.add(self.build_dir/'RPMS'/dir/file)

      for rpm in rpms:
        sftp.get(str(rpm), str(self.rpmsdir/rpm.basename))
  
    finally:
      # close connection
      if 'sftp' in locals(): sftp.close()

class SrpmBuild(Build):
  def __init__(self, definition, *args, **kwargs):
    self.definition = definition
    Build.__init__(self, *args, **kwargs)

  def _get_definition(self, options, arguments):
    self.definition = self.definition
    self.definitiontree = lxml.etree.ElementTree(self.definition)


# ------ Metaclass for creating SRPM Build Events -------- #
class SrpmBuildEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)

def __init__(self, ptr, *args, **kwargs):
  SrpmBuildMixinEvent.__init__(self, ptr, *args, **kwargs)


# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = [ ],
    description = 'modules that accept SRPMs and build RPMs',
  )

  # ensure unique srpm ids
  check_dup_ids(element = __name__.split('.')[-1],
                config = ptr.definition,
                xpath = '/*/srpmbuild/srpm/@id')

  # create event classes based on user configuration
  for config in ptr.definition.xpath('/*/srpmbuild/srpm', []):

    # convert user provided id to a valid class name
    id = config.get('@id')
    name = re.sub('[^0-9a-zA-Z_]', '', id)
    name = '%sSrpmBuildEvent' % name.capitalize()

    # create new class
    exec """%s = SrpmBuildEvent('%s', 
                         (SrpmBuildMixinEvent,), 
                         { 'srpmid'   : '%s',
                           '__init__': __init__,
                         }
                        )""" % (name, name, id) in globals()

    # update module info with new classname
    module_info['events'].append(name)

  return module_info


# -------- Error Classes --------#
class SrpmBuildEventError(CentOSStudioEventError): 
  message = ("%(message)s")

class InvalidRepoError(SrpmBuildEventError):
  message = ("Cannot retrieve repository metadata (repomd.xml) for repository "
             "'%(url)s'. Please verify its path and try again.\n")

class SrpmNotFoundError(SrpmBuildEventError):
  message = "No srpm '%(name)s' found at '%(path)s'\n"

class BuildMachineCreationError(SrpmBuildEventError):
  message = ("Error creating or updating RPM build machine.\n%(sep)s\n"
             "%(idstr)s--> build machine definition: %(definition)s\n--> "
             "error:\n%(error)s\n")
