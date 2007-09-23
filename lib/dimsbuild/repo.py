import csv
import xml.sax
import os

from gzip import GzipFile

from dims import pps
from dims import xmltree

from dimsbuild.constants import BOOLEANS_TRUE

P = pps.Path

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

#------ FACTORY FUNCTIONS ------#
def RepoFromXml(xml):
  repo = Repo(xml.get('@id'))
  repo.remote_path   = P(xml.get('path/text()'))
  repo.gpgcheck      = xml.get('gpgcheck/text()', 'False') in BOOLEANS_TRUE
  repo.gpgkeys       = [ P(path) for path in xml.xpath('gpgkey/text()', []) ]
  repo.repodata_path = xml.get('repodata-path/text()', '')
  repo.include       = xml.xpath('include/package/text()', [])
  repo.exclude       = xml.xpath('exclude/package/text()', [])
  
  return repo
