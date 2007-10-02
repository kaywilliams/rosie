import csv
import xml.sax
import os

from gzip import GzipFile

from dims import pps

from dims.xml import tree as xmltree

from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.logging   import L1, L2

P = pps.Path

class RepoContainer:
  def __init__(self):
    self.repos = {}
    
  def add_repo(self, id, **kwargs):
    repo = Repo(id)
    if not kwargs.has_key('local_path'):
      raise KeyError("The 'local_path' attribute is required to build a Repo object")
    if not kwargs.has_key('remote_path'):
      raise KeyError("The 'remote_path' attribute is required to build a Repo object")
    if not kwargs.has_key('pkgsfile'):
      kwargs['pkgsfile'] = P(kwargs['local_path']) / 'packages'
    for attr in kwargs.keys():
      setattr(repo, attr, kwargs[attr])
    self.repos[repo.id] = repo
    return repo

  def read_packages(self, write=True, id=None):
    if id is None: id = self.repos.keys()
    if not hasattr(id, '__iter__'): id = [id]
    for i in id:
      repo = self.repos[i]
      repo.readRepoData()
      repo.readRepoContents()
      if write:
        repo.writeRepoContents(repo.pkgsfile)

class Repo:
  def __init__(self, id):
    self.id = id
    
    self.remote_path = None
    self.local_path = None
    
    self.gpgcheck = False
    self.gpgkeys = []
    
    self.username = None
    self.password = None
    
    self.pkgsfile = None
    self.repoinfo = []
    
    self.include = []
    self.exclude = []
    
    self.repodata_path = ''
    self.mdfile = 'repodata/repomd.xml'
    self.datafiles = {}

    self.parser = xml.sax.make_parser()
  
  def rjoin(self, *args):
    p = self.remote_path
    for arg in args: p = p / arg
    return p
  
  def ljoin(self, *args):
    p = self.local_path
    for arg in args: p = p / arg
    return p
  
  def readRepoData(self, repomd=None, tmpdir=None):
    tmpdir = P(tmpdir or os.getcwd())
    if repomd is None: 
      tmpfile = tmpdir / 'repomd.xml'
      self.rjoin(self.repodata_path, self.mdfile).cp(tmpdir)
      repomd = xmltree.read(tmpfile).xpath('//data')
      tmpfile.rm(force=True) 
    for data in repomd:
      repofile = P(data.get('location/@href'))
      filetype = data.get('@type')
      self.datafiles[filetype] = repofile.basename
  
  def readRepoContents(self, repofile=None):
    self.repoinfo = []    
    if repofile is None:
      pxml = GzipFile(filename=self.ljoin(self.repodata_path, 'repodata', self.datafiles['primary']),
                      mode='rt')
      handler = PrimaryXmlContentHandler()
      self.parser.setContentHandler(handler)
      self.parser.parse(pxml)
      pxml.close()
      
      for f,s,m in handler.pkgs:
        self.repoinfo.append({
          'file':  self.rjoin(self.repodata_path, f),
          'size':  s,
          'mtime': m,
          })
      self.repoinfo.sort()
    else:
      mr = repofile.open('r')
      mreader = csv.DictReader(mr, ['file', 'size', 'mtime'], lineterminator='\n')
      for item in mreader:
        self.repoinfo.append({
          'mtime': int(item['mtime']),
          'size':  int(item['size']),
          'file':  P(item['file']),
        })      
      mr.close()
  
  def compareRepoContents(self, oldfile, what=None):
    "@param what: the item to compare; one of 'mtime', 'size', or 'file'"
    oldpkgs = []
    newpkgs = self.repoinfo
    
    if oldfile.isfile():
      mr = oldfile.open('r')
      mreader = csv.DictReader(mr, ['file', 'size', 'mtime'], lineterminator='\n')
      for item in mreader:
        oldpkgs.append({
          'mtime': int(item['mtime']),
          'size':  int(item['size']),
          'file':  item['file'],
        })      
      mr.close()
    
    if what is None:
      oldpkgs.sort()
      newpkgs.sort()    
      return oldpkgs != newpkgs
    else:
      old = [ d[what] for d in oldpkgs ]
      new = [ d[what] for d in newpkgs ]
      old.sort()
      new.sort()
      return old != new
  
  def writeRepoContents(self, file):
    if file.exists():
      file.rm()
    file.touch()
    mf = file.open('w')
    mwriter = csv.DictWriter(mf, ['file', 'size', 'mtime'], lineterminator='\n')    
    for item in self.repoinfo:
      mwriter.writerow(item)
    mf.close()
    

class PrimaryXmlContentHandler(xml.sax.ContentHandler):
  def __init__(self):
    xml.sax.ContentHandler.__init__(self)
    self.pkgs = []
    
    self.mtime = None
    self.size  = None
    self.loc   = None
    
    self.pkgstart = False
    
  def startElement(self, name, attrs):
    if name == 'package':
      self.pkgstart = True
    elif self.pkgstart and name == 'location':
      self.loc = str(attrs.get('href'))
    elif self.pkgstart and name == 'size':
      self.size = int(attrs.get('package'))
    elif self.pkgstart and name == 'time':
      self.mtime = int(attrs.get('file'))
  
  def endElement(self, name):
    if name == 'package':
      self.pkgstart = False
      self.pkgs.append((self.loc, self.size, self.mtime))
