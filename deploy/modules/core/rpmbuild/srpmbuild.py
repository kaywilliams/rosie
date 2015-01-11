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
import lxml
import re
import rpm
import rpmUtils
import yum

from deploy.dlogging     import MSG_MAXWIDTH, L0, L1, L2
from deploy.errors       import (DeployError, DeployEventError, 
                                 DuplicateIdsError, MissingIdError)
from deploy.event        import Event, CLASS_META
from deploy.main         import Build
from deploy.options      import DeployOptionParser
from deploy.util         import magic 
from deploy.util         import pps 
from deploy.util         import rxml 

from deploy.util.difftest.filesdiff import ChecksumDiffTuple

from deploy.modules.shared import (ExecuteEventMixin, ShelveMixin, 
                                   RpmBuildMixin, RPM_EXT, RpmNotFoundError) 
from deploy.modules.shared.repos import DeployRepo

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

class SrpmBuildEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'srpmbuild',
      parentid = 'rpmbuild',
      ptr = ptr,
      properties = CLASS_META,
      version = '1.00',
      conditionally_comes_after = ['config-rpms'],
      suppress_run_message = True
    )

class SrpmBuildMixinEvent(RpmBuildMixin, ExecuteEventMixin, ShelveMixin, Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = '%s-srpm' % self.srpmid, 
      parentid = 'srpmbuild',
      ptr = ptr,
      version = 1.14,
      config_base = '/*/%s/srpm[@id=\'%s\']' % (self.moduleid, self.srpmid),
    )
  
    self.options = copy.deepcopy(ptr.options)
    self.options.macros.extend(['os:%s' % self.os,
                                'version:%s' % self.version,
                                'arch:%s' % self.arch])

    self.DATA = {
      'input':     set(),
      'config':    set(), # handle config using variables since 
                       # srpmlast macro causes script content
                       # to change across runs
      'variables': set(),
      'output':    set(),
    }
  
    self.srpmfile = ''
    self.srpmdir  = self.mddir / 'srpm'

    self.rpmsdir   = self.mddir / 'rpms'

    self.data_root   = self.LOCAL_ROOT / 'srpms'
    for d in [ self.LOCAL_ROOT, self.data_root ]:
      d.exists() or d.mkdir()
      d.chmod(0700)
      d.chown(0,0)

    self.DATA['variables'].add('data_root')

    if self.version == "5":
      self.build_dir = pps.path('/usr/src/redhat')
    else:
      self.build_dir = pps.path('/root/rpmbuild')

    self.originals_dir = self.build_dir / 'originals'

    ShelveMixin.__init__(self)
    RpmBuildMixin.__init__(self)
    ExecuteEventMixin.__init__(self)
 
  def setup(self):
    self.diff.setup(self.DATA)

    # use checksums to better handle runtime-generated files (e.g. by 
    # srpmbuild scripts)
    self.diff.input.tupcls = ChecksumDiffTuple

    ExecuteEventMixin.setup(self)
    RpmBuildMixin.setup(self)
 
    # add config content to variables diff
    self.confvar = str(self.config).strip()
    self.DATA['variables'].add('confvar')

    # resolve macros
    srpmlast = self.unshelve('srpmlast', 'None') 
    macros = {'%{srpm-id}': self.srpmid,
              '%{srpm-dir}': self.srpmdir,
              '%{srpm-last}': srpmlast,
             }
    self.resolve_macros(map=macros)
  
    # get srpm
    path = pps.path(self.config.getxpath('path/text()', ''))
    repo = pps.path(self.config.getxpath('repo/text()', ''))
    script = self.config.getxpath('script/text()', '')
    if path: self._get_srpm_from_path(path)
    elif repo: self._get_srpm_from_repo(repo)
    elif script: self._get_srpm_from_script(script)

    # get rpms to exclude
    self.exclude_rpms = ' '.join(self.config.xpath('exclude/text()', []))

    # get default build machine definition template
    search_dirs = self.TEMPLATE_DIRS
    default = ''
    for d in [ x / self.norm_os for x in search_dirs]:
      results = d.findpaths(mindepth=1, type=pps.constants.TYPE_NOT_DIR,
                            glob='%s.xml' % self.moduleid)
      if results:
        default = results[0]
        break

    self.template = self.io.abspath(
                      pps.path(self.config.getxpath('/*/%s/template/text()'
                      % self.moduleid,
                      self.config.getxpath('template/text()', default)))
                      )
    self.io.validate_input_file(self.template)
    self.DATA['input'].add(self.template)

    if not self.template:
      raise DefinitionNotFoundError

  def run(self):
    # process srpm
    self._process_srpm()

    # start with a clean rpmsdir
    self.rpmsdir.rm(recursive=True, force=True)
    self.rpmsdir.mkdirs(mode=0700)

    # initialize builder
    # doing this in a method so dtest can call it directly
    self._initialize_builder()

    # build rpms
    if self.logger.threshold > 2:
      self.logger.log_header(3, "building '%s' SRPM" % self.srpmid)
    else:
      self.logger.log(2, L2("building '%s'" % self.srpmid))

    try:
      self.builder.main()
    except DeployError, e:
      raise BuildMachineCreationError(
                    template='based on \'%s\'' % self.template, 
                    error=e, idstr="--> build machine id: %s\n" %
                    self.builder.build_id, sep = MSG_MAXWIDTH * '=')

    self.logger.log(3, L0("%s" % '=' * MSG_MAXWIDTH))
    self.logger.log(3, L0(''))

    # verify rpms
    self.logger.log(3, L1("verifying rpms"))
    if hasattr(self, 'test_verify_rpms'): # set by test module
      badfile = self.rpmsdir / 'badfile'
      badfile.write_text('')

    rpmfiles = self.rpmsdir.findpaths(mindepth=1)
    if not rpmfiles:
      message = ("The build process for '%s' did not output any RPMs." % 
                 self.srpmfile.basename)
      raise SrpmBuildEventError(message=message)
    for file in rpmfiles:
      if magic.match(file) != magic.FILE_TYPE_RPM:
        message = ("The file at '%s' does not appear to be an rpm." % file)
        raise SrpmBuildEventError(message=message)

    # use RpmBuildMixin to sign rpms, cache rpmdata, and add rpms as output
    self.rpms = [ self._get_rpmbuild_data(f) for f in rpmfiles ]
    RpmBuildMixin.run(self)

  def _get_srpm_from_path(self, path):
    if not path.endswith(RPM_EXT['srpm']):
      path = path / self.srpmid

    self._setup_rpm_from_path(path, dest=self.srpmdir, type='srpm')

  def _get_srpm_from_repo(self, baseurl):
    # cache repodata to mddir and have yum read it from there
    repo = DeployRepo(baseurl=baseurl)
    try:
      repo.read_repomd()
    except pps.Path.error.PathError, e:
      message = ("unable to read metadata for the repo at '%s'\n\n%s:" %
                 (baseurl, e))
      raise SrpmBuildEventError(message=message)


    repodata_dir = self.mddir / 'repodata'
    repodata_dir.mkdirs(mode=0700)
    
    # download repomd and primary files for use in offline mode
    self.link(repo.url/repo.repomdfile, repodata_dir)
    self.link(repo.url/repo.getdatafile('primary').href, repodata_dir)

    localurl = 'file://' + self.mddir
    yumconf = self.mddir / 'yum.conf'
    yumconf.write_text(YUMCONF % (self.id, localurl))

    yb = yum.YumBase()
    yb.preconf.fn = str(yumconf)
    yb.preconf.root = str(self.mddir)
    yb.preconf.init_plugins = False
    yb.preconf.errorlevel = 0
    yb.doRpmDBSetup()
    yb.conf.cache = 0
    yb.doRepoSetup(self.id)
  
    try:
      yb.doSackSetup(archlist=['src'], thisrepo=self.id)
    except yum.Errors.RepoError:
      raise InvalidRepoError(url=baseurl)
  
    try:
      srpm = (yb.repos.getRepo(self.id).getPackageSack()
              .returnNewestByName(name=self.srpmid)[0])
    except yum.Errors.PackageSackError:
      raise SrpmNotFoundError(name=self.srpmid, path=baseurl)
      
    self.io.add_fpath(srpm.remote_url.replace(localurl, baseurl), 
                      self.srpmdir, id='srpm')
    del yb; yb = None

  def _get_srpm_from_script(self, script):
    self.srpmdir.mkdirs(mode=0700)
    script_file = self.mddir / 'script'
    script_file.write_text(self.config.getxpath('script/text()').encode('utf8'))
    script_file.chmod(0700)
 
    self._local_execute(script_file, script_id='srpmbuild script')
  
    results = self.srpmdir.findpaths(glob='%s-*.src.rpm' % self.srpmid, 
                                     maxdepth=1)
  
    if not results:
      message = ("The script provided for the '%s' srpm did not output an "
                 "srpm beginning with '%s' and ending with '.src.rpm' in the "
                 "location specified by the %%{srpm-dir} macro ('%s'). See the "
                 "Deploy documentation for information on using the "
                 "srpm/script element." % (self.srpmid, self.srpmid, 
                                           self.srpmdir))
      raise SrpmBuildEventError(message=message)
    elif len(results) > 1:
      message = "more than one result: %s" % results
      raise SrpmBuildEventError(message=message)
    else:
      self.srpmfile = results[0]
      self.DATA['input'].add(self.srpmfile)

  def _process_srpm(self):
    self.io.process_files(cache=True)
    if self.srpmfile: # srpm provided by script
      self.DATA['output'].add(self.srpmfile)
    else: # srpm provided by path or repo
      self.srpmfile = self.io.list_output(what='srpm')[0]

    self.shelve('srpmlast', self.srpmfile)

  def _initialize_builder(self):
    try:
      self.builder = SrpmBuild(self, self._get_build_machine_options(), [],
                                     callback=None, error_handler=None)
    except DeployError, e:
      raise BuildMachineCreationError(
              template='based on \'%s\'' % self.template, 
              error=e, idstr='', sep = MSG_MAXWIDTH * '=',)

  def _get_build_machine_options(self):
    # get default deploy options
    opts,_ = DeployOptionParser().parse_args([])

    # override for use with srpmbuild
    opts.logthresh = self.logger.threshold
    opts.logfile = self.options.logfile
    opts.libpath = self.options.libpath
    opts.sharepath = self.options.sharepath
    opts.data_root = self.data_root
    opts.local_root = self.LOCAL_ROOT
    opts.force_events = ['deploy']
    opts.mainconfigpath = self.options.mainconfigpath
    opts.macros = self.options.macros
    opts.offline = self.options.offline
    opts.debug = self.options.debug
    
    return opts


class SrpmBuild(Build):
  def __init__(self, ptr, *args, **kwargs):
    self.ptr = ptr
    Build.__init__(self, *args, **kwargs)

  def _get_definition_path(self, *args):
    self.definition_path = self.ptr.template

  def _get_definition(self, options, arguments):
    name, spec, requires = self._get_srpm_info(self.ptr.srpmfile)

    Build._get_definition(self, options, arguments)

    # add config-rpm for srpm requires
    config = self.definition.getxpath('/*/config-rpms',
                                      rxml.config.Element('config-rpms'))
    rpm = rxml.config.Element('config-rpm', parent=config, 
                              attrib={'id': '%s-%s-config' %
                              (self.ptr.moduleid, self.ptr.srpmid)})
    child = rxml.config.Element('files', parent=rpm)
    child.set('destdir', self.ptr.originals_dir)
    child.text = self.ptr.srpmfile

    for req in requires:
      child = rxml.config.Element('requires', parent=rpm)
      child.text = req

    if self.definition.find('config') is None:
      self.definition.append(config)

    # use gpgsign from parent definition, if provided
    parent_gpgsign = copy.deepcopy(self.ptr.config.getxpath('/*/gpgsign', None))
    child_gpgsign = self.definition.getxpath('/*/gpgsign', None)
    if parent_gpgsign is not None and child_gpgsign is None:
      self.definition.append(parent_gpgsign)
     
    # append repos from parent definition, if provided
    if self.definition.getxpath('/*/repos', None) is None:
      rxml.config.Element('repos', parent=self.definition)
      
    parent_repos = {}
    for repo in self.ptr.config.getxpath('/*/repos', []):
      parent_repos[repo.get('id')] = repo

    child_repos = {}
    for repo in self.definition.getxpath('/*/repos', []):
      child_repos[repo.get('id')] = repo

    for id, elem in parent_repos.items():
      if elem not in child_repos.values():
        if id in child_repos:
          self.definition.getxpath('/*/repos', []).replace(child_repos[id],
                                                           elem.copy())
        else:
          self.definition.getxpath('/*/repos', []).append(elem.copy())

    #resolve macros
    self.definition.resolve_macros(map={
      '%{build-dir}':   self.ptr.build_dir,
      '%{srpm}':        self.ptr.originals_dir / self.ptr.srpmfile.basename,
      '%{spec}':        self.ptr.build_dir / 'SPECS' / spec,
      '%{rpms-dir}':    self.ptr.rpmsdir,
      '%{exclude-rpms}':self.ptr.exclude_rpms,
      },
      defaults_file=self.datfile_format)

    self.definition.remove_macros(defaults_file=self.datfile_format)

  def _get_srpm_info(self, srpm):
    ts = rpmUtils.transaction.initReadOnlyTransaction()
    hdr = rpmUtils.miscutils.hdrFromPackage(ts, srpm)
    name = hdr[rpm.RPMTAG_NAME]
    spec = [ f for f in hdr['FILENAMES'] if '.spec' in f ][0]
    requires = [ r.DNEVR()[2:] for r in hdr.dsFromHeader('requirename') ]
    del ts
    del hdr
    return (name, spec, requires) 


# ------ Metaclass for creating SRPM Build Events -------- #
class SrpmBuildRpmEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)

def __init__(self, ptr, *args, **kwargs):
  SrpmBuildMixinEvent.__init__(self, ptr, *args, **kwargs)


# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = ['SrpmBuildEvent'],
    description = 'modules that accept SRPMs and build RPMs',
  )

  srpmids = getattr(ptr, 'cvars[\'srpmids\']', [])

  # create event classes based on user configuration
  for config in ptr.definition.xpath('/*/srpmbuild/srpm', []):

    # convert user provided id to a valid class name
    id = config.getxpath('@id', None)
    if id == None:
      raise MissingIdError(config)
    name = re.sub('[^0-9a-zA-Z_]', '', id)
    name = '%sSrpmBuildEvent' % name.capitalize()

    # ensure unique srpm ids
    if id in srpmids:
      raise DuplicateIdsError(ptr.definition.xpath('./srpmbuild/srpm[@id="%s"]'
                                                    % id))

    # create new class
    exec """%s = SrpmBuildRpmEvent('%s', 
                         (SrpmBuildMixinEvent,), 
                         { 'srpmid'   : '%s',
                           '__init__': __init__,
                         }
                        )""" % (name, name, id) in globals()

    # update srpmids with new id
    srpmids.append(id)

    # update module info with new classname
    module_info['events'].append(name)

  # update cvars srpmids
  ptr.cvars['srpmids'] = srpmids

  return module_info


# -------- Error Classes --------#
class SrpmBuildEventError(DeployEventError): 
  message = ("%(message)s")

class InvalidRepoError(SrpmBuildEventError):
  message = ("Cannot retrieve repository metadata (repomd.xml) for repository "
             "'%(url)s'. Please verify its path and try again.\n")

class DefinitionNotFoundError(SrpmBuildEventError):
  message = ("No SRPM build machine definition template found. Please see the "
             "Deploy documentation for information on specifying SRPM "
             "build machine definition templates.\n")

class SrpmNotFoundError(RpmNotFoundError, SrpmBuildEventError):
  def __init__(self, name, path):
    RpmNotFoundError(name, path, type='srpm')

class BuildMachineCreationError(SrpmBuildEventError):
  message = ("Error creating or updating SRPM build machine.\n%(sep)s\n"
             "%(idstr)s--> build machine definition template: "
             "%(template)s\n--> "
             "error:\n%(error)s\n")
