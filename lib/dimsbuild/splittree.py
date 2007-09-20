import copy
import os
import re
import rpm

from math    import ceil

from dims import FormattedFile as ffile
from dims import pkgorder

from dims.xmltree import XmlTreeElement

from dimsbuild.constants import RPM_GLOB, SRPM_GLOB

TS = rpm.TransactionSet()
TS.setVSFlags(-1)

SIZE_REGEX = re.compile('[\s]*([\d]+(?:\.[\d]+)?)[\s]*([kKmMgG]?)[bB]?[\s]*$')

SIZE_ALIASES = {
  'CD':  '640MB',
  'DVD': '4.7GB'
}

ORDINALS = ['', 'K', 'M', 'G']

class Timber:
  "Split trees like no other"
  def __init__(self, discsize='640MB', dosrc=False):
    self.discsize = parse_size(discsize)
    if self.discsize < (100 * (1024**2)): # 104857600 bytes, 100 MB
      raise ValueError, "Minimum disc size for iso generation is 100 MB"
    self.dosrc = dosrc
    self.comps = 10 * (1024**2) # 10 MB
    self.reserve = 0
    self.product = None
    self.pkgorder = None
    
    # the following must be pps.Path objects
    self.u_tree = None     # unified tree
    self.u_src_tree = None # uniifed source tree
    self.s_tree = None     # split tree
    
    self.rpm_disc_map = None
    self.srpm_disc_map = None
    
    self.reverse_srpms = False
    
    self.discinfo_vars = None
    self.common_files = [] #!
    self.difmt = None
    
  def create_discinfo(self, discnumber):
    "Create a .discinfo file for disc number in split tree"
    if isinstance(self.difmt, dict):
      discinfo = ffile.DictToFormattedFile(self.difmt)
    elif isinstance(self.difmt, XmlTreeElement):
      discinfo = ffile.XmlToFormattedFile(self.difmt)
    else:
      raise ValueError, "Unsupported format %s for pkgorder.difmt" % type(self.difmt)
    
    if self.discinfo_vars is None:
      difile = self.u_tree/'.discinfo'
      if not difile.exists():
        raise RuntimeError, "Error: .discinfo doesn't exist in unified tree"
      self.discinfo_vars = discinfo.read(difile)
    vars = copy.copy(self.discinfo_vars)
    vars['discs'] = str(discnumber)
    discinfo.write(
      self.s_tree/'%s-disc%d' % (self.product, discnumber)/'.discinfo',
      **vars
    )
  
  def link(self, src, dst, files):
    "Link each file in src/[files] to dest/[files]"
    for file in files:
      (src/file).cp(dst, link=True, recursive=True)
  
  def cleanup(self):
    self.s_tree.glob('%s-disc*' % self.product).rm(recursive=True, force=True)
  
  def compute_layout(self):
    srpm_nregex = '.*\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]'
    
    # rpms
    totalsize = self.u_tree.findpaths(nregex=srpm_nregex).getsize()
    rpmsize = self.u_tree.findpaths(glob=RPM_GLOB, nregex=srpm_nregex).getsize()
    
    extrasize = totalsize - rpmsize
    
    ndiscs = int(ceil(float(totalsize)/self.discsize))
    nrpmdiscs = self.__consume_discs(rpmsize + extrasize)
    self.rpm_disc_map = range(1, nrpmdiscs + 1)
    
    # srpms
    nsrpmdiscs = 0
    if self.dosrc:
      srpmsize = self.u_src_tree.findpaths(glob=SRPM_GLOB).getsize()
      ndiscs = int(ceil(float(srpmsize)/self.discsize))
      nsrpmdiscs = self.__consume_discs(srpmsize)
      self.srpm_disc_map = range(nrpmdiscs + 1, nrpmdiscs + nsrpmdiscs + 1)
    
    self.numdiscs = nrpmdiscs + nsrpmdiscs
      
  def __consume_discs(self, size):

    i_size = 0
    num_discs = 0
    while i_size < size:
      num_discs += 1
      i_size += self.discsize
    return num_discs
  
  def split_trees(self):
    "Split stuff up"
    #shared = range(self.total_discs - (self.srpm_discs or 0) + 1, self.rpm_discs + 1)
    
    ##print self.rpm_disc_map, self.rpm_discs
    ##print self.srpm_disc_map, self.srpm_discs
    ##print shared, self.total_discs
    
    for i in self.rpm_disc_map:
      discpath = self.s_tree/'%s-disc%d' % (self.product, i)
      (discpath/self.product).mkdirs()
      if i == 1: # put release files on disc 1
        for file in self.u_tree.findpaths(
            nregex='.*(\..*|.*\.[Rr][Pp][Mm]|(S)?RPMS|%s)$' % self.product,
            mindepth=1, maxdepth=1):
          file.cp(discpath, link=True, recursive=True)
      else:
        self.link(self.u_tree, discpath, self.common_files)
      self.create_discinfo(i)
    
    if self.dosrc:
      for i in self.srpm_disc_map:
        discpath = self.s_tree/'%s-disc%d' % (self.product, i)
        (discpath/'SRPMS').mkdirs()
        self.link(self.u_tree, discpath, self.common_files)
        self.create_discinfo(i)

  def split_rpms(self):
    packages = {}
    pkgdir = self.u_tree/self.product
    
    for rpm in pkgdir.findpaths(glob='*.[Rr][Pp][Mm]'):
      size = rpm.getsize()
      pkgnvra = nvra(rpm)
      
      if packages.has_key(pkgnvra):
        packages[pkgnvra].append(rpm)
      else:
        packages[pkgnvra] = [rpm]
    
    order = pkgorder.parse_pkgorder(self.pkgorder)
    for i in range(0, len(order)):
      order[i] = pkgtup_to_nvra(order[i])
    
    disc = self.rpm_disc_map[0]
    discpath = self.s_tree/'%s-disc%d' % (self.product, disc)
    
    used = discpath.findpaths().getsize()
    for rpmnvra in order:
      if not packages.has_key(rpmnvra): continue
      
      newsize = used
      
      for file in packages[rpmnvra]:
        if (discpath/self.product/file).exists(): continue
        
        size = file.getsize()
        assert size > 0
        newsize = used + size
        
        if disc == 1: maxsize = self.discsize - self.comps - self.reserve
        else:         maxsize = self.discsize
        
        if newsize > maxsize:
          # move to the next disc
          try:
            nextdisc = self.rpm_disc_map.index(disc+1)
            disc = self.rpm_disc_map[nextdisc]
            discpath = self.s_tree/'%s-disc%d' % (self.product, disc)
            self.link(pkgdir, discpath/self.product, [file])
          except (IndexError, ValueError):
            disc = disc - 1
            print 'DEBUG: overflow from disc %d onto disc %d' % (disc+1, disc)
            print 'DEBUG: newsize: %d maxsize: %d' % (newsize, maxsize)
            continue
        else:
          self.link(pkgdir, discpath/self.product, [file])
      used = newsize
  
  def split_srpms(self):
    if not self.dosrc:
      return
    
    srpms = self.u_src_tree.findpaths(glob='*.[Ss][Rr][Cc].[Rr][Pp][Mm]')
    
    srpms.sort('size')
    
    # keep list of SRPM trees and their sizes
    sizes = []
    for disc in self.srpm_disc_map:
      sizes.append(
        [ (self.s_tree/'%s-disc%d' % (self.product, disc)).findpaths().getsize(),
          disc ]
      )
    sizes.sort()
    
    # add srpm to the smallest source tree
    for srpm in srpms:
      (self.u_src_tree/srpm).link(self.s_tree/'%s-disc%d/SRPMS/%s' % \
        (self.product, sizes[0][1], srpm.basename))
      sizes[0][0] += srpm.getsize()
      sizes.sort()
  

def nvra(pkgfile):
  fd = os.open(pkgfile, os.O_RDONLY)
  h = TS.hdrFromFdno(fd)
  os.close(fd)
  return '%s-%s-%s.%s' % (h['name'], h['version'], h['release'], h['arch'])

def pkgtup_to_nvra(pkgtup):
  return '%s-%s-%s.%s' % (pkgtup[0], pkgtup[3], pkgtup[4], pkgtup[1])

def parse_size(size):
  if type(size) == type(0):
    pass
  elif type(size) == type(0.0):
    return int(size)
  elif type(size) == type(''):
    size = size.upper()
    if size in SIZE_ALIASES:
      size = SIZE_ALIASES[size]
    try:
      size, ord = SIZE_REGEX.match(size).groups() # raises AttributeError if no match
      size = float(size)
      ord = ord.upper()
      size = size * (1024**ORDINALS.index(ord)) # raises ValueError if not found
    except (AttributeError, ValueError), e:
      print e
      raise ValueError, 'unrecognizable size: %s' % size
  else:
    raise ValueError, 'unrecognized type: %s' % type(size)
  
  return int(round(size))
