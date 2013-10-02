import copy
import fnmatch
import re

from deploy.util import pps
from deploy.util import rxml

__all__ = ['BaseRepo', 'IORepo', 'YumRepo', 'RepoContainer', 'RPM_PNVRA_REGEX',
           'RepoDuplicateIdsError']

RPM_PNVRA_REGEX = re.compile('(?P<path>.*/)?'  # all chars up to the last '/'
                             '(?P<name>.+)'    # rpm name
                             '-'
                             '(?P<version>.+)' # rpm version
                             '-'
                             '(?P<release>.+)' # rpm release
                             '\.'
                             '(?P<arch>.+)'    # rpm architecture
                             '\.[Rr][Pp][Mm]')


class BaseRepo(dict):
  "Python representation of a software repository (e.g. a yum repo)"
  isep = ' = '
  keyfilter = ['id'] # list of keys to not include in stringification

  def __init__(self, **kwargs):
    dict.__init__(self, **kwargs)

    self.vars = {} # dict of substr:replace values (use with $yumvars, for ex.)

  @property
  def id(self):         return self.get('id', None)
  @property
  def name(self):       return self.get('name', None)
  @property
  def baseurl(self):    return [ self._xform_uri(p) for p in
                                 (self.get('baseurl', '') or '').split() ]
  @property
  def mirrorlist(self):
    ml = self.get('mirrorlist', None)
    # convert local paths to file:///... paths
    if ml: return self._xform_uri(ml)

  def get(self, key, *args, **kwargs):
    "Automatically does _var_replace on items retrieved from the repo."
    # if you do not want this var replacement, use dict.get directly
    item = dict.get(self, key, *args, **kwargs)
    return self._var_replace(item)

  def _var_replace(self, s):
    "replace substrings in items with values provided"
    if s is None: return s # sometimes we're passed None, this is OK
    if isinstance(s, basestring):
      for k,v in self.vars.items():
        s = s.replace(str(k), str(v))
      return s
    else:
      r = []
      for i in s:
        r.append(self._var_replace(i))
      return r

  def __str__(self):
    return self.tostring(pretty=True)

  def tostring(self, pretty=False, doreplace=False, **updates):
    return '\n'.join(self.lines(pretty=pretty, **updates))+'\n'

  def lines(self, pretty=False, doreplace=False, **updates):
    lines = ['[%s]' % self.id]

    # apply any updates
    repo = copy.copy(self)
    repo.update(updates)

    # compute formatting information - value depends on pretty
    if pretty:
      longest = 0
      for k,v in repo.items():
        if v or updates.get(k,None):
          if len(k) > longest:
            longest = len(k)
      fmt1 = '%%(key)-%ds%s%%(value)s' % (longest, self.isep)
      fmtN = '%s%%(value)s' % (' '*(longest+len(self.isep)))
    else:
      fmt1 = '%%(key)s%s%%(value)s' % self.isep
      fmtN = None

    for k in repo.keys():
      if k in self.keyfilter: continue # don't include filtered keys
      try:
        v = getattr(repo, k)
      except AttributeError:
        v = repo.get(k)
      if v is not None:
        if k == 'include': k = 'includepkgs' # translate to yum terminology
        line = self._itemsplit(k, v, fmt1=fmt1, fmtN=fmtN, pretty=pretty)
        if doreplace: line = self._var_replace(line)
        lines.append(line)

    # yum doesn't like it when repos don't have a name
    if not repo.has_key('name'):
      line = self._itemsplit('name', repo.id, fmt1=fmt1, fmtN=fmtN, pretty=pretty)
      if doreplace: line = self._var_replace(line)
      lines.append(line)
    return lines

  def _itemsplit(self, itemid, items, fmt1=None, fmtN=None, pretty=False):
    fmt1 = fmt1 or ''
    fmtN = fmtN or ''
    if isinstance(items, basestring):
      return fmt1 % dict(key=itemid, value=items)
    elif isinstance(items, bool):
      return fmt1 % dict(key=itemid, value=items and 'yes' or 'no')
    # otherwise its a list
    if pretty:
      items = items[:] # copy so we dont mess things up
      for i in range(0, len(items)):
        if i == 0:
          items[i] = fmt1 % dict(key=itemid, value=items[i])
        else:
          items[i] = fmtN % dict(value=items[i])
      return '\n'.join(items)
    else:
      return fmt1 % dict(key=itemid, value=' '.join(items))

  def _xform_uri(self, p):
    return pps.path(p).touri()

  def toxml(self, fn=rxml.tree.Element):
    repo = fn('repo', attrib={'id': self.id})
    for k,v in self.items():
      if k in self.keyfilter: continue
      # make sure we split up multiple items into individual elements
      if v:
        for i in self._itemsplit(k, v, fmt1='%(value)s').split():
          fn(k, text=i, parent=repo)
    return repo


NSMAP = dict(repo   = 'http://linux.duke.edu/metadata/repo',
             common = 'http://linux.duke.edu/metadata/common')

class IORepo(BaseRepo):
  "Adds repodata IO functionality to BaseRepo"

  repomdfile = pps.path('repodata/repomd.xml')

  def __init__(self, **kwargs):
    BaseRepo.__init__(self, **kwargs)

    self._url = None    # cache of our url
    self.datafiles = {} # dict of file type:location pairs
    self.repomd = None  # repomd in xml format

  # properties for dealing with sqlite files
  @property
  def sqlite_files(self):
    return dict([ (k,v) for k,v in self.datafiles.items()
                  if      k.endswith('_db')
                  and not k.startswith('group') ])
  @property
  def nonsqlite_files(self):
    return dict([ (k,v) for k,v in self.datafiles.items()
                  if  not k.endswith('_db')
                  and not k.startswith('group') ])
  @property
  def has_sqlite(self):
    return len(self.sqlite_files.keys()) > 0

  # properties for dealing with groupfile
  # these are kind of stupid, but they're here for parity with the above
  # properties
  @property
  def gz_group(self):
    return dict([ (k,v) for k,v in self.datafiles.items()
                  if k == 'group_gz' ])
  @property
  def nongz_group(self):
    return dict([ (k,v) for k,v in self.datafiles.items()
                  if k == 'group' ])
  @property
  def has_gz(self):
    return len(self.gz_group.keys()) > 0

  def getdatafile(self, type):
    # return datafile of specified type (e.g. primary) in the relevant format
    # (e.g. sqllite if sqlite suported)
    if self.has_sqlite:
      return [v for k,v in self.sqlite_files.items() if k.startswith(type)][0]
    else:
      return [v for k,v in self.nonsqlite_files.items() if k.startswith(type)][0] 
    if self.has_gz:
      return [v for k,v in self.gz_group.items() if k.startswith(type)][0] 
    else:
      return [v for k,v in self.nongz_group.items() if k.startswith(type)][0] 

  def iterdatafiles(self, all=False):
    # if all is true, iterate over all datafiles, otherwise only the ones
    # that make sense (sqlite if sqlite supported, else normals)
    if all:
      return iter(self.datafiles.values())

    datafiles = []
    if self.has_sqlite:
      datafiles.extend(self.sqlite_files.values())
    else:
      datafiles.extend(self.nonsqlite_files.values())
    if self.has_gz:
      datafiles.extend(self.gz_group.values())
    else:
      datafiles.extend(self.nongz_group.values())
    return iter(datafiles)

  def read_repomd(self):
    try:
      self.repomd = rxml.tree.parse((self.url//self.repomdfile).open()
                                     ).getroot()
    except rxml.errors.XmlSyntaxError:
      raise InvalidFileError("The repository metadata file at %s does not "
                             "appear to be valid"
                             % (self.url//self.repomdfile)) 

    for data in self.repomd.xpath('repo:data', namespaces=NSMAP):
      self.datafiles[data.getxpath('@type')] = RepoDataFile(data)

  def cache_repodata(self, p, what=None):
    "Cache the repo's repodata to p"
    if not self.datafiles:
      self.read_repomd()

    if not what: what = self.datafiles.keys()
    elif isinstance(what, basestring): what = [what]

    p = pps.path(p)
    assert p.exists(), "Destination '%s' does not exist" % p
    d = p/'repodata'
    d.mkdirs()
    for fid in what:
      fp = self.url // self.datafiles[fid]
      fp.cp(d, preserve=True)

  @property
  def url(self):
    if not self._url:
      # if baseurl or mirrorgroup changes we'll have to refresh url
      if not self.baseurl and not self.mirrorlist:
        raise ValueError("Repo '%s' does not specify baseurl or mirrorlist" % self.id)

      urls = []
      if self.baseurl and len(self.baseurl) == 1 and not self.mirrorlist:
        # single baseurl, don't create a mirror path
        self._url = self.baseurl[0]

      else:
        # create a MirrorPath
        if self.baseurl:
          urls.extend(self.baseurl)
          if not self.mirrorlist:
            # first baseurl serves as mirrorlist key if we don't otherwise have one
            self._url = pps.path('mirror:%s::/' % self.baseurl[0])
        if self.mirrorlist:
          self._url = pps.path('mirror:%s::/' % self.mirrorlist)
          # retry reading mirrorlist 5 times on 502 errors (see retry502, below)
          ml = pps.lib.mirror.validate_mirrorlist(
                 retry502(5, self.mirrorlist.read_lines))
          ml = filter(pps.lib.mirror.MirrorGroup._filter, ml)
          if len(ml) == 0:
            raise pps.Path.mirror.MirrorlistEmptyError(self._url)
          urls.extend(ml)

        assert self._url

        # prepopulate the mirrorgroup cache so we don't go trying to read
        # baseurl[0] like a mirrorlist (and so it reflects the additional
        # baseurl mirrors we want to add)
        pps.Path.mirror.mgcache[self._url] = pps.lib.mirror.MirrorGroup(urls)

    return self._url

class RepoDataFile:
  def __init__(self, xml):
    self.href = pps.path(xml.getxpath('repo:location/@href', namespaces=NSMAP))
    self.checksum = xml.getxpath('repo:checksum/text()', namespaces=NSMAP)
    self.checksum_type = xml.getxpath('repo:checksum/@type', namespaces=NSMAP)
    self.timestamp = xml.getxpath('repo:timestamp/text()', namespaces=NSMAP)

def retry502(times, fn, *args, **kwargs):
  """Some urls (namely mirrors.fedoraproject.org/mirrorlist) like to raise
  502 errors with some regularity.  502 shouldn't normally result in a retry;
  however, these errors seem to resolve themselves in short order normally,
  at least with this website.  This function attempts to correct for this
  problem."""
  i = 0
  while i < times:
    try:
      return fn(*args, **kwargs)
    except pps.Path.error.PathError, e:
      if hasattr(e.exception, 'code') and e.exception.code == 502:
        i += 1; continue
      else:
        raise
  raise # if we get this far, we've errored every time; reraise the last one


class YumRepo(IORepo):
  "A yum repository"

  def __init__(self, **kwargs):
    IORepo.__init__(self, **kwargs)

    self.repocontent = _RepoContent() # contains parsed data about repo contents
    self.repocontent.repo = self # I wish I could pass this in __init__

  def _boolparse(self, s):
    if s in ['0', 'no', 'false']:
      return False
    elif s in ['1', 'yes', 'true']:
      return True
    elif s is None:
      return None
    else:
      raise ValueError('invalid boolean value')

  @property
  def gpgkey(self):      return [ self._xform_uri(p) for p in
                                  (self.get('gpgkey', '') or '').split() ]
  @property
  def gpgcheck(self):    return self._boolparse(self.get('gpgcheck', 'no'))
  @property
  def exclude(self):     return self.get('exclude', '').split()
  @property
  def include(self): return self.get('include', '').split()
  @property
  def enabled(self):     return self._boolparse(self.get('enabled', 'yes'))

  # hack to allow updating gpgkeys
  def extend_gpgkey(self, list):
    self['gpgkey'] = self.get('gpgkey','') + ' ' + ' '.join(list)

class RepoContainer(dict):
  "A container for other repos (a yum.conf file, for example)"
  def __str__(self):
    return self.tostring(pretty=True, doreplace=False)

  def tostring(self, *args, **kwargs):
    s = ''
    for repo in self.values():
      s += repo.tostring(*args, **kwargs)+'\n'
    return s

  # TODO - make ignore_duplicates a class property
  def add_repo(self, repo, ignore_duplicates=False, **kwargs):
    if not self.has_key(repo.id):
      self[repo.id] = repo
    else:
      if ignore_duplicates:
        return
      else:
        raise RepoDuplicateIdsError(id=repo.id)
    self[repo.id].update(**kwargs)

  def add_repos(self, repocontainer, **kwargs):
    for repo in repocontainer.values():
      self.add_repo(repo, **kwargs)


import csv
try:
  import sqlite3 as sqlite
except ImportError: # RedHat 5/CentOS 5 don't have sqlite3
  import sqlite

from gzip     import GzipFile
from StringIO import StringIO
from xml.sax  import make_parser, ContentHandler

from yum.misc import unique, bunzipFile

from deploy.util import magic

CSVORDER = ['file', 'size', 'mtime']

class _RepoContent(list):
  def __init__(self, *args, **kwargs):
    list.__init__(self, *args, **kwargs)
    self.repo = None # pointer back to the repo this is associated with
    self.pkgdict = None

  def clear(self):
    del self[:]

  def update(self, data, clear=True):
    "Read the primary.xml(s) into self"
    if isinstance(data, basestring): data = [data]

    if clear: self.clear()

    for f in data:
      fname = self.repo.localurl / f
      ftype = magic.match(fname)
      if ftype == magic.FILE_TYPE_GZIP:
        get_package_tups = self._update_xml
      elif ftype == magic.FILE_TYPE_BZIP2:
        get_package_tups = self._update_sqlite
      else:
        raise ValueError(ftype)

      for url,size,mtime in get_package_tups(fname):
        self.append(dict(
          file  = pps.path(f.splitall()[:-2] or '')//url,
          size  = size,
          mtime = mtime))

    self.sort()
    self._gen_pkgdict()

  def _update_xml(self, f):
    fpxml = GzipFile(f, 'rt')
    handler = PrimaryXmlContentHandler()
    parser = make_parser()
    parser.setContentHandler(handler)
    parser.parse(fpxml)
    fpxml.close()
    fpxml.filename = None # memory leak fix?
    del fpxml

    return handler.pkgs

  def _update_sqlite(self, f):
    fsqlite = f.dirname/f.basename.splitext()[0] # remove .bz2
    try:
      bunzipFile(f, fsqlite) # imported from yum.misc
      conn = sqlite.connect(fsqlite)
      c = conn.cursor()
      c.execute('SELECT location_href, size_package, time_file '
                'FROM   packages')
      return list(c) # copy list so we can close sqlite stuff
    finally:
      c.close()
      conn.close()
      fsqlite.remove()

  def read(self, f):
    "Read a csv file with <filename>,<size>,<mtime> lines into self"
    self._fromcsv(f)

  def write(self, fn):
    "Write self into <filename>,<size>,<lines> lines at in file fn"
    pps.path(fn).write_lines(self._tocsv())

  def filter(self, include=None, exclude=None):
    ret = []
    if include is None: include = self.repo.include
    if exclude is None: exclude = self.repo.exclude

    # only include matching rpms
    toadd = []
    if include:
      for pkgpattern in include:
        for match in fnmatch.filter(self.pkgdict.keys(), pkgpattern):
          toadd.append(self.pkgdict[match])
    else:
      toadd = self.pkgdict.values()
    toadd = unique(toadd)

    todel = []
    if exclude:
      for pkgpattern in exclude:
        for match in fnmatch.filter(self.pkgdict.keys(), pkgpattern):
          todel.append(self.pkgdict[match])
    todel = unique(todel)

    ret = toadd[:]
    for i in todel:
      try:    ret.remove(i)
      except: pass

    return ret

  def has_package(self, pkg):
    "Return True iff this repo has a package of the given name"
    pkgs = []
    if self.repo.include:
      for pkgpattern in self.repo.include:
        pkgs += fnmatch.filter(self.pkgdict.keys(), pkgpattern)
    else:
      pkgs += self.pkgdict.keys()
    for pkgpattern in self.repo.exclude:
      for toremove in fnmatch.filter(pkgs, pkgpattern):
        try:    pkgs.remove(toremove)
        except: pass

    return pkg in pkgs

  def _gen_pkgdict(self):
    self.pkgdict = {}
    for pkg in self:
      n,a,e,v,r = pkgtup(pkg['file'])
      self.pkgdict[n] = pkg
      self.pkgdict['%s.%s' % (n,a)] = pkg
      self.pkgdict['%s-%s-%s.%s' % (n,v,r,a)] = pkg
      self.pkgdict['%s-%s' % (n,v)] = pkg
      self.pkgdict['%s-%s-%s' % (n,v,r)] = pkg
      self.pkgdict['%s:%s-%s-%s.%s' % (e,n,v,r,a)] = pkg
      self.pkgdict['%s-%s:%s-%s.%s' % (n,e,v,r,a)] = pkg

  def return_pkgs(self, fmt=None, include=None, exclude=None):
    fmt = fmt or '$name-$version-$release.$arch'
    ret = []
    for pkg in self.filter(include=include, exclude=exclude):
      n,a,e,v,r = pkgtup(pkg['file'])
      ret.append( fmt.replace('$name', n)
                     .replace('$arch', a)
                     .replace('$epoch', e)
                     .replace('$version', v)
                     .replace('$release', r) )
    return ret


class PrimaryXmlContentHandler(ContentHandler):
  def __init__(self):
    ContentHandler.__init__(self)
    self.pkgs = [] # list of file, size, mtime tuples for content

    self._pkgdata = {}  # list of current package data
    self._inpkg = False # are we in a <package> element?

  def startElement(self, name, attrib):
    if name == 'package':
      self._inpkg = True
    elif self._inpkg:
      if name == 'location':
        self._pkgdata['file']  = pps.path(str(attrib.get('href')))
      elif name == 'size':
        self._pkgdata['size']  = int(attrib.get('package'))
      elif name == 'time':
        self._pkgdata['mtime'] = int(attrib.get('file'))

  def endElement(self, name):
    if name == 'package':
      self._inpkg = False
      self.pkgs.append((self._pkgdata['file'],
                        self._pkgdata['size'],
                        self._pkgdata['mtime']))

def pkgtup(pkgpath):
  # TODO - add (better) epoch support
  try:
    p,n,v,r,a = RPM_PNVRA_REGEX.match(str(pkgpath)).groups()
    return (n,a,'0',v,r)
  except AttributeError:
    return (None, None, None, None, None)

class InvalidFileError(RuntimeError): pass

class RepoDuplicateIdsError(StandardError):
  def __init__(self, id):
    self.id = id
    self.message = "Duplicate ids found: '%s'" % self.id

  def __str__(self):
    return self.message
  
