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
import re
import rpmUtils 
import yum

from centosstudio.util import pps 

from centosstudio.util.pps.constants import TYPE_NOT_DIR

from centosstudio.errors  import (CentOSStudioEventError,
                                  SimpleCentOSStudioEventError)
from centosstudio.event    import Event, CLASS_META

from centosstudio.modules.shared import (ExecuteMixin, PickleMixin, 
                                         SystemVirtConfigError)


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

# -------- Metaclass for creating SRPM Build Events -------- #
class SrpmBuildEvent(type):
  def __new__(meta, classname, supers, classdict):
    return type.__new__(meta, classname, supers, classdict)


# -------- Methods for SRPM Build Events -------- #
def __init__(self, ptr, *args, **kwargs):
  Event.__init__(self,
    id = '%s-%s' % (self.moduleid, self.srpmid), 
    parentid = 'rpmbuild',
    ptr = ptr,
    version = 1.02,
    requires = ['rpmbuild-data', 'build-machine'],
    provides = ['repos', 'source-repos', 'comps-object'],
    config_base = '/*/%s/srpm[@id=\'%s\']' % (self.moduleid, self.srpmid),
  )

  try:
    exec "import libvirt" in globals()
    exec "from virtinst import CloneManager" in globals()
  except ImportError:
    raise SystemVirtConfigError(file=self._config.file)

  self.DATA = {
    'input':     [],
    'config':    ['.'],
    'variables': [],
    'output':    [],
  }

  self.srpmfile = ''
  self.srpmdir  = self.mddir / 'srpm'
  PickleMixin.__init__(self)

def setup(self):
  self.diff.setup(self.DATA)
  ExecuteMixin.setup(self)

  # resolve macros
  srpmlast = self.unpickle().get('srpmlast', '')
  macros = {'%{srpm-id}': self.srpmid,
            '%{srpm-dir}': self.srpmdir,
            '%{srpm-last}': srpmlast,
           }
  self.config.resolve_macros('.', macros)

  path = pps.path(self.config.get('path/text()', ''))
  repo = pps.path(self.config.get('repo/text()', ''))
  script = self.config.get('script/text()', '')

  # add srpm from file path
  if path: 
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

  # add srpm from package repository
  elif repo:
    yumdir = self.mddir / 'yum'
    yumdir.mkdirs()
    yumconf = yumdir / 'yum.conf'
    yumconf.write_text(YUMCONF % (self.id, repo))
    yb = yum.YumBase()
    yb.preconf.fn = fn=str(yumconf)
    yb.preconf.root = str(yumdir)
    yb.preconf.init_plugins = False
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

  # add srpm from user-provided script 
  elif script:
    # start with a clean srpmdir
    self.srpmdir.rm(recursive=True, force=True) 
    self.srpmdir.mkdirs()

    script_file = self.mddir / 'script'
    script_file.write_text(self.config.get('script/text()'))
    script_file.chmod(0750)

    self._execute_local(script_file)

    results = self.srpmdir.findpaths(glob='%s-*.src.rpm' % self.srpmid, 
                                      maxdepth=1)

    if not results:
      message = ("The script provided for the '%s' srpm did not output an "
                 "srpm beginning with '%s' and ending with '.src.rpm' in the "
                 "location specified by the %%{srpmdir} macro. See the "
                 "CentOS Studio documentation for information on using the "
                 "srpm/script element." % (self.srpmid, self.srpmid))
      raise SimpleCentOSStudioEventError(message=message)
    elif len(results) > 1:
      message = "more than one result: %s" % results
      raise SimpleCentOSStudioEventError(message=message)
    else:
      self.srpmfile = results[0]
      self.DATA['input'].append(self.srpmfile)

def run(self):
  self.io.process_files(cache=True)

  # cache srpm file and info
  if self.srpmfile: # srpm provided by script
    self.DATA['output'].append(self.srpmfile)
  else: # srpm provided by path or repo
    self.srpmfile = self.io.list_output(what='srpm')[0] 
  self.pickle({'srpmlast': self.srpmfile.basename})
  
  #clone build machine
  self._clone()

  #build rpm
  #verify rpm

def _clone(self):
  clone_name = '%s-%s-%s-%s' % (self.moduleid, self.srpmid, self.version,
                                self.userarch)

  connection = libvirt.open('qemu:///system')
  domain = connection.lookupByName(self.cvars['build-machine'])

  design = CloneManager.CloneDesign(conn=connection) #fix qemu errors
  design.original_guest = self.cvars['build-machine']
  design.clone_name = clone_name #fix qemu errors
  design.set_preserve(True)
  
  design.setup_original() # needed to get original_devices below

  for device in design.original_devices:
    design.clone_devices = CloneManager.generate_clone_disk_path(device, design)

  design.setup()

  #fix spurious warnings
  #raise RuntimeError

  #pause machine if running
  #try/finally block to destroy, undefine and delete storage

# -------- provide module information to dispatcher -------- #
def get_module_info(ptr, *args, **kwargs):
  module_info = dict(
    api         = 5.0,
    events      = [ ],
    description = 'modules that accept SRPMs and build RPMs',
  )

  # create event classes based on user configuration
  for config in ptr.definition.xpath('/*/srpmbuild/srpm', []):

    # convert user provided id to a valid class name
    id = config.get('@id')
    name = re.sub('[^0-9a-zA-Z_]', '', id)
    name = '%sSrpmBuildEvent' % name.capitalize()

    # create new class
    exec """%s = SrpmBuildEvent('%s', 
                          (ExecuteMixin, PickleMixin, Event), 
                          { 'srpmid'   : '%s',
                            '__init__': __init__,
                            'setup'   : setup,
                            'run'     : run,
                            '_clone'  : _clone,
                          }
                         )""" % (name, name, id) in globals()

    # update module info with new classname
    module_info['events'].append(name)

  return module_info


# -------- Error Classes --------#
class InvalidRepoError(CentOSStudioEventError):
  message = ("Cannot retrieve repository metadata (repomd.xml) for repository "
             "'%(url)s'. Please verify its path and try again.\n")

class SrpmNotFoundError(CentOSStudioEventError):
  message = "No srpm '%(name)s' found at '%(path)s'\n" 
