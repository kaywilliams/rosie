import csv
import os
import re
import xml.sax

from gzip import GzipFile

from dims import pps
from dims import xmllib

from dimsbuild.constants import BOOLEANS_TRUE, BOOLEANS_FALSE

sep = ' = ' # the separator between key and value

DEFAULTSECT = 'main'

# SECTRE, OPTCRE, and RepoContainer._read taken right out of python's ConfigParser
# Regular expressions for parsing section headers and options.
SECTCRE = re.compile(
  r'\['                        # [
  r'(?P<header>[^]]+)'         # very permissive!
  r'\]'                        # ]
)
OPTCRE = re.compile(
  r'(?P<option>[^:=\s][^:=]*)' # very permissive!
  r'\s*(?P<vi>[:=])\s*'        # any number of space/tab, followed by separator
                               # (: or =), followed by any number of space/tab
  r'(?P<value>.*)$'            # everything up to eol
)

NSMAP = {'repo': 'http://linux.duke.edu/metadata/repo',
         'common': 'http://linux.duke.edu/metadata/common'}

P = pps.Path

class RepoContainer(dict):
  def __init__(self, ptr):
    self.ptr = ptr

  "Python representation of a yum .repo file"
  def __str__(self):
    s = ''

    if self.has_key(DEFAULTSECT):
      s += '[%s]\n' % DEFAULTSECT
      for k,v in self[DEFAULTSECT].items():
        if   v in BOOLEANS_TRUE:  v = '1'
        elif v in BOOLEANS_FALSE: v = '0'
        s += '%s%s%s\n' % (k, sep, str(v).replace('\n', '\n' + ' '*(len(k+sep))))
      s += '\n'

    for k,v in self.items():
      if k != DEFAULTSECT:
        s += str(v)

    return s

  def write(self, fp):
    fp.write(self.__str__())

  def add_repo(self, id, **kwargs):
    if not self.has_key(id):
      self[id] = Repo({'id': id})
    self[id].update(kwargs)

  def read_config(self, tree):
    for repo in tree.xpath('repo'):
      id = repo.get('@id')
      self[id] = Repo({'id': id})
      self[id].read_config(repo)

  def read(self, filenames):
    if isinstance(filenames, basestring):
      filenames = [filenames]
    read_ok = []
    for filename in filenames:
      filename = P(filename)
      if isinstance(filename, pps.path.file.FilePath): #! bad
        filename = (P(self.ptr._config.file).dirname / filename).normpath()
      fp = open(filename)
      self._read(fp, filename)
      fp.close()
      read_ok.append(filename)
    return read_ok

  def readfp(self, fp, filename=None):
    if filename is None:
      try:
        filename = fp.name
      except AttributeError:
        filename = '<???>'
    self._read(fp, filename)

  def _read(self, fp, fpname):
    cursect = None  # None, or a dictionary
    optname = None
    lineno = 0
    e = None        # None, or an exception

    while True:
      line = fp.readline()
      if not line:
        break
      lineno += 1
      # comment or blank line?
      if line.strip() == '' or line[0] in '#;':
        continue
      # continuation line?
      if line[0].isspace() and cursect is not None and optname:
        value = line.strip()
        if value:
          cursect[optname] = "%s\n%s" % (cursect[optname], value)
      # a section header or option header?
      else:
        # is it a section header?
        mo = SECTCRE.match(line)
        if mo:
          sectname = mo.group('header')
          if sectname in self.keys():
            cursect = self[sectname]
          elif sectname == DEFAULTSECT:
            cursect = self.setdefault(DEFAULTSECT, {})
          else:
            cursect = self.setdefault(sectname, Repo({'id': sectname}))
          # So sections can't start with a continuation line
          optname = None
        # no section header in the file?
        elif cursect is None:
          raise ValueError("File contains no section headers.\nfile: %s, line %d\n%r" % (fpname, lineno, line))
        # an option line?
        else:
          mo = OPTCRE.match(line)
          if mo:
            optname, vi, optval = mo.group('option', 'vi', 'value')
            if vi in ('=', ':') and ';' in optval:
              # ';' is a comment delimiter only if it follows
              # a spacing character
              pos = optval.find(';')
              if pos != -1 and optval[pos-1].isspace():
                optval = optval[:pos]
            optval = optval.strip()
            # allow empty values
            if optval == '""':
              optval = ''
            cursect[optname.rstrip()] = optval
          else:
            # a non-fatal parsing error
            if not e: e = ParsingError(fpname)
            e.append(lineno, repr(line))
    # if any parsing errors occurred, raise an exception
    if e:
      raise e


class Repo(dict):
  "Python representation of a repo inside a yum .repo file"
  def __init__(self, *args, **kwargs):
    dict.__init__(self, *args, **kwargs)

    self.localurl = None
    self.pkgsfile = None
    self.mdfile = 'repodata/repomd.xml'

    self.repoinfo = []
    self.datafiles = {}

    self._parser = xml.sax.make_parser()

  def __str__(self):
    s = '[%s]\n' % self['id']
    for k,v in self.items():
      if isinstance(v, pps.path.file.FilePath): #! hack to make sure file:// is prepended
        v = 'file://%s' % v
      if   v in BOOLEANS_TRUE:  v = '1'
      elif v in BOOLEANS_FALSE: v = '0'
      s += '%s%s%s\n' % (k, sep, str(v).replace('\n', '\n' + ' '*(len(k+sep))))
    s += '\n'
    return s

  def read_config(self, tree):
    self['id'] = tree.get('@id')
    self['name'] = tree.get('name/text()', self['id'])
    # this baseurl stuff will have to be addressed when we work on supporting
    # mirrorgroups and multiple baseurls
    ##self['baseurl'] = '\n'.join(tree.xpath('path/text()'))
    self['baseurl'] = P(tree.get('baseurl/text()')) #!
    if tree.pathexists('gpgcheck/text()'):
      self['gpgcheck'] = tree.get('gpgcheck/text()')
    if tree.pathexists('gpgkey/text()'):
      self['gpgkey'] = '\n'.join(tree.xpath('gpgkey/text()'))
    if tree.pathexists('exclude/package/text()'):
      self['exclude'] = ' '.join(tree.xpath('exclude/package/text()'))
    if tree.pathexists('includepkgs/package/text()'):
      self['includepkgs'] = ' '.join(tree.xpath('includepkgs/package/text()'))

  def update_metadata(self):
    self._read_repodata()
    self._read_repo_content()

  def _read_repodata(self):
    repomd = xmllib.tree.read((self.remoteurl/self.mdfile).open())

    for data in repomd:
      repofile = P(data.get('repo:location/@href', namespaces=NSMAP))
      filetype = data.get('@type')
      self.datafiles[filetype] = repofile.basename

  def _read_repo_content(self, repofile=None):
    self.repoinfo = []
    if not repofile:
      pxml = GzipFile(filename=self.localurl/'repodata'/self.datafiles['primary'],
                      mode='rt')
      handler = PrimaryXmlContentHandler()
      self._parser.setContentHandler(handler)
      self._parser.parse(pxml)
      pxml.close()
      pxml.filename = None # memory leak somehow?
      del pxml

      for f,s,m in handler.pkgs:
        self.repoinfo.append({
          'file':  self.remoteurl/f,
          'size':  s,
          'mtime': m,
          })
      self.repoinfo.sort()

    else:
      self.repoinfo.extend(make_repoinfo(repofile))

  def compare_repo_content(self, oldfile, what=None):
    "@param what: the item to compare; one of 'mtime', 'size', or 'file'"
    oldpkgs = []
    newpkgs = self.repoinfo

    if oldfile.isfile():
      oldpkgs.extend(make_repoinfo(oldfile))

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

  def write_repo_content(self, file):
    if file.exists(): file.rm()
    file.touch()
    mf = file.open('w')
    mwriter = csv.DictWriter(mf, ['file', 'size', 'mtime'], lineterminator='\n')
    for item in self.repoinfo:
      mwriter.writerow(item)
    mf.close()

  def _get_gpgkeys(self): return self._get_val('gpgkey')
  def _get_include(self): return self._get_val('include')
  def _get_exclude(self): return self._get_val('exclude')
  def _get_val(self, key, splitter=None):
    if self.has_key(key):
      return self[key].split(splitter)
    else:
      return []

  # handy properties based on dictionary values
  id = property(lambda self: self['id'])
  remoteurl = property(lambda self: P(self['baseurl']))
  gpgkeys = property(_get_gpgkeys)
  include = property(_get_include)
  exclude = property(_get_exclude)


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


def make_repoinfo(file):
  repoinfo = []
  mr = file.open('r')
  mreader = csv.DictReader(mr, ['file', 'size', 'mtime'], lineterminator='\n')
  for item in mreader:
    repoinfo.append({
      'mtime': int(item['mtime']),
      'size':  int(item['size']),
      'file':  item['file'],
    })
  mr.close()
  return repoinfo


class ParsingError(Exception):
  "Raised when a configuration file does not follow legal syntax."

  def __init__(self, filename):
    self.message = 'File contains parsing errors: %s' % filename
    self.filename = filename
    self.errors = []

  def append(self, lineno, line):
    self.errors.append((lineno, line))
    self.message += '\n\t[line %2d]: %s' % (lineno, line)
