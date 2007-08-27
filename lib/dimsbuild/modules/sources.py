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
    'id': 'sources',
    'provides': ['SRPMS',],
    'requires': ['software', 'new-rpms', 'rpms-directory', 'source-repo-contents'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  },
  {
    'id': 'source-repos',
    'provides': ['input-source-repos-changed',
                 'local-source-repodata',
                 'source-repo-contents',
                 'source-include'],
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'interface': 'SrpmInterface',
  }
]

HOOK_MAPPING = {
  'SourcesHook':    'sources',
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
    self.interface.validate('/distro/sources', 'sources.rng')
    
class SourceRepoHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.source-repos'
    self.interface = interface

    self.mdsrcrepos = join(self.interface.METADATA_DIR, 'source-repos')
    
    self.DATA = {
      'config': ['/distro/sources'],
      'input':  [],
      'output': [],
    }
    self.mdfile = join(self.interface.METADATA_DIR, 'source-repos.md')

    if self.interface.config.pathexists('/distro/sources') and \
       self.interface.config.get('/distro/sources/@enabled', 'True') in BOOLEANS_TRUE:
      self.dosource = True
    else:
      self.dosource = False

  def setup(self):    
    self.interface.setup_diff(self.mdfile, self.DATA)
    if self.dosource:
      self.srcrepos = {}
      osutils.mkdir(self.mdsrcrepos, parent=True)
      for repoxml in self.interface.config.xpath('/distro/sources/repo'):
        repo = RepoFromXml(repoxml)
        repo.local_path = join(self.mdsrcrepos, repo.id)
        repo.pkgsfile = join(self.mdsrcrepos, '%s.pkgs' % repo.id)
        
        o = self.interface.setup_sync(paths=[(repo.rjoin(repo.repodata_path, 'repodata'),
                                              repo.ljoin(repo.repodata_path))])
        self.DATA['output'].extend(o)
        self.DATA['output'].append(repo.pkgsfile)
          
        repo.getRepoData()
        
        self.srcrepos[repo.id] = repo

        self.DATA['output'].append(repo.ljoin(repo.repodata_path, 'repodata'))
        self.DATA['output'].append(join(self.interface.METADATA_DIR, '%s.pkgs' % repo.id))
        self.srcrepos[repo.id] = repo

  def clean(self):
    self.interface.log(0, "cleaning source-repos event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    if not self.dosource:
      self.clean()
      return
    self.interface.log(0, "processing input source repositories")
    self.interface.sync_input()

    self.interface.log(1, "reading available packages")
    self.interface.repoinfo = {}
    for repo in self.srcrepos.values():
      self.interface.log(2, repo.id)

      # read repomd.xml
      repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
      repo.readRepoData(repomd)

      # read primary.xml
      repo.readRepoContents()
      repo.writeRepoContents(repo.pkgsfile)

    if self.interface.has_changed('input'):
      self.interface.cvars['input-source-repos-changed'] = True
    
  def apply(self):
    ## write_metadata() should be called here because if self.dosource
    ## is False and there is no source element in the config file,
    ## ConfigHandler.diff() is always going to return True because
    ## the metadata file doesn't exist because of which '/distro/sources'
    ## is a NewEntry() and diff(NewEntry, NoneEntry) is going to return
    ## True.    
    self.interface.write_metadata()    
    self.interface.cvars['source-include'] = self.dosource
    self.interface.cvars['local-source-repodata'] = self.mdsrcrepos
    if self.dosource:
      self.interface.cvars['source-repos'] = self.srcrepos
      if not self.interface.cvars['input-source-repos-changed']:      
        for repo in self.srcrepos.values():
          repomdfile = repo.ljoin(repo.repodata_path, repo.mdfile)
          for file in repomdfile, repo.pkgsfile:
            if not exists(file):
              raise RuntimeError("Unable to find cached file at '%s'. Perhaps you " \
                                 "are skipping the 'source-repos' event before it has "\
                                 "been allowed to run once?" % file)
          repomd = xmltree.read(repo.ljoin(repo.repodata_path, repo.mdfile)).xpath('//data')
          repo.readRepoData(repomd)
          repo.readRepoContents(repofile=repo.pkgsfile)

class SourcesHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'sources.sources'
    
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
    
    o = self.interface.setup_sync(paths=paths)
    self.DATA['output'].extend(o)

  def clean(self):
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()

  def check(self):
    return self.interface.cvars['new-rpms'] or \
           not exists(self.interface.srpmdest) or \
           self.interface.test_diffs()  

  def run(self):
    if not self.dosource:
      self.clean()
      return

    self.interface.log(0, "processing srpms")
    self.interface.remove_output()
    osutils.mkdir(self.interface.srpmdest, parent=True)
    self.interface.sync_input()
    self.interface.createrepo()

    self.interface.write_metadata()
