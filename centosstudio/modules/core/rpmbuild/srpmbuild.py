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

from centosstudio.modules.shared import ExecuteMixin

YUMCONF = '''
[main]
cachedir=
logfile=/depsolve.log
gpgcheck=0
reposdir=/
reposdir=/
exclude=*debuginfo*

[srpm_repo]
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
    id = self.srpmid + "-srpm", # self.srpmid provided during class creation
    parentid = 'rpmbuild',
    ptr = ptr,
    version = 1.01,
    requires = ['rpmbuild-data', 'build-machine'],
    provides = ['repos', 'source-repos', 'comps-object'],
    config_base = '/*/rpmbuild/srpm[@id=\'%s\']' % self.srpmid,
  )

  self.DATA = {
    'input':     [],
    'config':    ['.'],
    'variables': [],
    'output':    [],
  }

  self.srpm_dir = self.mddir / 'srpm'
  self.srpm_dir.mkdirs()

  self.macros = {'%{srpmid}': self.srpmid,
                 '%{srpm-dir}': self.srpm_dir,
                }


def setup(self):
  self.diff.setup(self.DATA)
  ExecuteMixin.setup(self)

  path = pps.path(self.config.get('path/text()', ''))
  repo = pps.path(self.config.get('repo/text()', ''))
  script = self.config.get('script/text()', '')

  if path: # add srpm from file path
    if path.endswith('.src.rpm'): # add the file
      self.io.add_xpath('path', self.srpm_dir) # fileio performs validation

    else: # add the most current matching srpm
      srpms = path.findpaths(type=TYPE_NOT_DIR, mindepth=1, maxdepth=1, 
                             glob='%s*' % self.srpmid)
      if not srpms: 
        raise SrpmNotFoundError(name=self.srpmid, path=path)

      while len(srpms) > 1:
        print "srpms:", srpms
        srpm1 = srpms.pop()
        srpm2 = srpms.pop()
        _,v1,r1,e1,_  = rpmUtils.misc.splitFilename(srpm1.basename)
        _,v2,r2,e2,_  = rpmUtils.misc.splitFilename(srpm2.basename)
        result = rpmUtils.misc.compareEVR((e1,v1,r1),(e2,v2,r2))
        if result < 1: # srpm2 is newer, return it to the list
          srpms.insert(0, srpm2)
        else: # srpm1 is newer, or they are the same
          srpms.insert(0, srpm1)

      self.io.add_xpath('path', self.srpm_dir)

  elif repo: # find srpm in srpm repository
    yumconf = self.mddir / 'yum/yum.conf'
    yumconf.dirname.mkdirs()
    yumconf.write_text(YUMCONF % repo)

    try:
      yb = yum.YumBase()
      yb.preconf.fn = fn=str(yumconf)
      yb.preconf.root = str(self.mddir / 'yum')
      yb.preconf.init_plugins = False
      yb.doRpmDBSetup()
      yb.conf.cache = 0
      yb.doRepoSetup()
      yb.doSackSetup(archlist=['src'])
      pl = yb.doPackageLists(patterns=[self.srpmid])
      del yb; yb = None
    except yum.Errors.RepoError, e:
      raise InvalidRepoError(url=repo)

    if pl.available:
      self.io.add_fpath( repo / '%s.rpm' % str(pl.available[0]), self.srpm_dir )
    else:
      raise SrpmNotFoundError(name=self.srpmid, path=repo)

  elif script: # execute user-provided script 
    script_file = self.mddir / 'script'
    script_file.write_text(self.config.get('script/text()'))
    script_file.chmod(0750)

    self._execute_local(script_file)

    results = self.srpm_dir.findpaths(glob='%s-*.src.rpm' % self.srpmid, 
                                      maxdepth=1)

    if not results:
      message = ("The script provided for the '%s' srpm did not output an "
                 "srpm beginning with '%s' and ending with '.src.rpm' in the "
                 "location specified by the %%{srpm-dir} macro. See the "
                 "CentOS Studio documentation for information on using the "
                 "srpm/script element." % (self.srpmid, self.srpmid))
      raise SimpleCentOSStudioEventError(message=message)
    elif len(results) > 1:
      message = "more than one result: %s" % results
      raise SimpleCentOSStudioEventError(message=message)
    else:
      self.DATA['input'].append(results[0])

def run(self):
  self.io.process_files(cache=True)
  
  #test if rpm with same nevra already exists
  
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
                          (ExecuteMixin, Event), 
                          { 'srpmid'   : '%s',
                            '__init__': __init__,
                            'setup'   : setup,
                            'run'     : run,
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
