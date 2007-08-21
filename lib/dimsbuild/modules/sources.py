""" 
sources.py

downloads srpms 
"""

__author__  = 'Daniel Musgrave <dmusgrave@abodiosoftware.com>'
__version__ = '1.1'
__date__    = 'June 12th, 2007'

import os
import re
import rpm

from StringIO import StringIO
from os.path  import join, exists
from rpm      import TransactionSet, RPMTAG_SOURCERPM

from dims import osutils
from dims import shlib 
from dims import spider
from dims import sync
from dims import xmltree

from dims.configlib import uElement

from dimsbuild.constants import BOOLEANS_TRUE, RPM_GLOB, SRPM_GLOB, SRPM_PNVRA
from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from dimsbuild.interface import EventInterface, RepoFromXml, Repo

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'source',
    'provides': ['SRPMS',],
    'requires': ['software', 'new-rpms', 'rpms-directory', 'source-repo-contents'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
  {
    'id': 'source-repos',
    'provides': ['local-source-repodata',
                 'source-repo-contents',
                 'source-include'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  }
]

HOOK_MAPPING = {
  'SourceHook':     'source',
  'ValidateHook':   'validate',
  'SourceRepoHook': 'source-repos',
}

SRPM_PNVRA_REGEX = re.compile(SRPM_PNVRA)

class SrpmInterface(EventInterface):
  def __init__(self, base):
    EventInterface.__init__(self, base)    
    self.srpmdest = join(self.OUTPUT_DIR, 'SRPMS')
    
  def getAllSourceRepos(self):
    return self.cvars['source-repos'].values()
  
  def deformat(self, srpm):
    try:
      return SRPM_PNVRA_REGEX.match(srpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract srpm information from name '%s'" % srpm)
      return (None, None, None, None, None)

  def nvr(self, srpm):
    "nvr = SoftwareInterface.nvr(rpm) - convert an RPM filename into an NVR string"
    _,n,v,r,_ = self.deformat(srpm)
    return '%s-%s-%s' % (n,v,r)    

  def createrepo(self):
    "Run createrepo on the output store"
    pwd = os.getcwd()
    os.chdir(self.srpmdest)
    self.log(1, "running createrepo")
    shlib.execute('/usr/bin/createrepo -q .')
    os.chdir(pwd)

#------ HOOKS ------#
class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/source', 'sources.rng')
    
class SourceRepoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source-repos'
    self.interface = interface

    self.mdsrcrepos = join(self.interface.METADATA_DIR, 'source-repos')
    
    self.DATA = {
      'config': ['/distro/source'],
      'input':  [],
      'output': [],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'source-repos.md')
    if self.interface.config.pathexists('/distro/source') and \
       self.interface.config.get('/distro/source/@enabled', 'True') in BOOLEANS_TRUE:
      self.dosource = True
    else:
      self.dosource = False

  def clean(self):
    self.interface.clean_metadata()

  def setup(self):    
    self.interface.cvars['source-repos'] = {}
    self.interface.setup_diff(self.mdfile, self.DATA)
    
    if self.dosource:    
      self.interface.log(0, "generating filelists for input source repositories")
      osutils.mkdir(self.mdsrcrepos, parent=True)
      
      # sync all repodata folders to builddata
      self.interface.log(1, "synchronizing repository metadata")
      for repoxml in self.interface.config.xpath('/distro/source/repo'):
        self.interface.log(2, repoxml.get('@id'))
        repo = RepoFromXml(repoxml)
        repo.local_path = join(self.mdsrcrepos, repo.id)
        
        repo.getRepoData()
        
        self.interface.cvars['source-repos'][repo.id] = repo

        self.DATA['output'].append(repo.ljoin(repo.repodata_path, 'repodata'))
        self.DATA['output'].append(join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id))

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    if not self.dosource:
      self.interface.remove_output(parent=self.interface.METADATA_DIR, all=True)
      return
    else:
      self.interface.remove_output(parent=self.interface.METADATA_DIR)

    self.interface.log(1, "computing source repo contents")      
    for repo in self.interface.getAllSourceRepos():
      self.interface.log(2, repo.id)
      repo.readRepoContents()
      repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
      if repo.compareRepoContents(repofile):
        repo.changed = True
        repo.writeRepoContents(repofile)
    
  def apply(self):
    self.interface.cvars['source-include'] = self.dosource
    self.interface.write_metadata()    
    if self.dosource:
      # populate the srpms list for each repo
      for repo in self.interface.getAllSourceRepos():
        repofile = join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id)
        if not exists(repofile):
          raise RuntimeError("Unable to find repo file '%s'" % repofile)

        ## It is a lot faster to read a CSV file as compared to an XML file :)
        repo.readRepoContents(repofile=repofile)
    
    self.interface.cvars['local-source-repodata'] = self.mdsrcrepos


class SourceHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source'
    
    self.interface = interface
    
    self.DATA =  {
      'input':  [],
      'output': [],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'source.md')    
      
  def setup(self):
    self.mdsrcrepos = self.interface.cvars['local-source-repodata']    
    self.dosource = self.interface.cvars['source-include']
    
    self.interface.setup_diff(self.mdfile, self.DATA)
    if not self.dosource: return

    # compute the list of SRPMS
    self.ts = TransactionSet()
    self.ts.setVSFlags(-1)    
    srpmlist = []
    for pkg in osutils.find(self.interface.cvars['rpms-directory'],
                            name=RPM_GLOB):
      i = os.open(pkg, os.O_RDONLY)
      h = self.ts.hdrFromFdno(i)
      os.close(i)
      srpm = h[RPMTAG_SOURCERPM]
      if srpm not in srpmlist:
        srpmlist.append(srpm)

    # populate input and output lists
    paths = []
    for repo in self.interface.getAllSourceRepos():
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        size = rpminfo['size']
        mtime = rpminfo['mtime']
        _,n,v,r,a = self.interface.deformat(rpm)        
        nvra = '%s-%s-%s.%s.rpm' %(n,v,r,a) ## assuming the prefix to be lower-case 'rpm' suffixed
        if nvra in srpmlist:
          paths.append(((rpm, size, mtime), self.interface.srpmdest))

    self.DATA['input'].append(self.mdsrcrepos)
    self.DATA['output'].append(join(self.interface.srpmdest, 'repodata'))
    
    i,o = self.interface.getFileLists(paths=paths)
    self.DATA['input'].extend(i)
    self.DATA['output'].extend(o)

  def clean(self):
    self.interface.remove_output(parent=self.interface.OUTPUT_DIR, all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.cvars['new-rpms'] or \
           not exists(self.interface.srpmdest) or \
           self.interface.test_diffs()  

  def run(self):
    if not self.dosource:
      self.interface.remove_output(parent=self.interface.OUTPUT_DIR, all=True)
      return
    else:
      self.interface.remove_output(parent=self.interface.OUTPUT_DIR)

    self.interface.log(0, "processing srpms")
    osutils.mkdir(self.interface.srpmdest, parent=True)
    self.interface.sync_input()
    self.interface.createrepo()

  def apply(self):
    self.interface.write_metadata()
