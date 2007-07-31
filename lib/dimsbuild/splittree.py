import copy
import os
import re
import rpm

from math    import ceil
from os.path import exists, isfile, isdir, join

import dims.FormattedFile as ffile
import dims.pkgorder      as pkgorder
import dims.osutils       as osutils

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
    self.unified_tree = None
    self.unified_source_tree = None
    self.split_tree = None
    
    self.rpm_disc_map = None
    self.srpm_disc_map = None
    
    self.reverse_srpms = False
    
    self.discinfo_vars = None
    self.common_files = [] #!
    self.difmt = None
    
  def create_discinfo(self, discnumber):
    "Create a .discinfo file for disc number in split tree"
    if type(self.difmt) == type({}):
      discinfo = ffile.DictToFormattedFile(self.difmt)
    elif type(self.difmt == type('')):
      discinfo = ffile.XmlToFormattedFile(self.difmt)
    else:
      raise ValueError, "Unsupported format %s for pkgorder.difmt" % type(self.difmt)
    
    if self.discinfo_vars is None:
      if not exists(join(self.unified_tree, '.discinfo')):
        raise RuntimeError, "Error: .discinfo doesn't exist in unified tree"
      self.discinfo_vars = discinfo.read(join(self.unified_tree, '.discinfo'))
    vars = copy.copy(self.discinfo_vars)
    vars['discs'] = str(discnumber)
    discinfo.write(join(self.split_tree,
                        '%s-disc%d' % (self.product, discnumber),
                        '.discinfo'), **vars)
  
  def link(self, src, dest, files):
    "Link each file in src/[files] to dest/[files]"
    for file in files:
      osutils.cp(join(src, file), dest, link=True, recursive=True)
  
  def cleanup(self):
    osutils.rm(join(self.split_tree, '%s-disc*' % self.product), recursive=True, force=True)
  
  def compute_layout(self):
    srpm_nregex = '.*\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]'
    
    # rpms
    totalsize = osutils.du(osutils.find(self.unified_tree, nregex=srpm_nregex))
    rpmsize = osutils.du(osutils.find(self.unified_tree, name='*.[Rr][Pp][Mm]',
                                      nregex=srpm_nregex))
    
    extrasize = totalsize - rpmsize
    
    ndiscs = int(ceil(float(totalsize)/self.discsize))
    nrpmdiscs = self.__consume_discs(rpmsize + extrasize)
    self.rpm_disc_map = range(1, nrpmdiscs + 1)
    
    # srpms
    nsrpmdiscs = 0
    if self.dosrc:
      srpmsize = osutils.du(osutils.find(self.unified_source_tree,
                                         name='*.[Ss][Rr][Cc].[Rr][Pp][Mm]'))
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
      discpath = join(self.split_tree, '%s-disc%d' % (self.product, i))
      osutils.mkdir(join(discpath, self.product), parent=True)
      if i == 1: # put release files on disc 1
        for file in filter(None, osutils.find(self.unified_tree,
            nregex='.*(\.discinfo|.*\.[Rr][Pp][Mm]|(S)?RPMS|%s)' % self.product,
            mindepth=1, maxdepth=1)):
          osutils.cp(file, discpath, link=True, recursive=True)
      else:
        self.link(self.unified_tree, discpath, self.common_files)
      self.create_discinfo(i)
    
    if self.dosrc:
      for i in self.srpm_disc_map:
        discpath = join(self.split_tree, '%s-disc%d' % (self.product, i))
        osutils.mkdir(join(discpath, 'SRPMS'), parent=True)
        self.link(self.unified_tree, discpath, self.common_files)
        self.create_discinfo(i)

  def split_rpms(self):
    packages = {}
    pkgdir = join(self.unified_tree, self.product)
    
    rpms = osutils.find(pkgdir, name='*.[Rr][Pp][Mm]')
    rpms.sort()
    
    for rpm in rpms:
      size = os.path.getsize(join(pkgdir, rpm))
      pkgnvra = nvra(join(pkgdir, rpm))
      
      if packages.has_key(pkgnvra):
        packages[pkgnvra].append(rpm)
      else:
        packages[pkgnvra] = [rpm]
    
    order = pkgorder.parse_pkgorder(self.pkgorder)
    for i in range(0, len(order)):
      order[i] = pkgtup_to_nvra(order[i])
    
    disc = self.rpm_disc_map[0]
    discpath = join(self.split_tree, '%s-disc%d' % (self.product, disc))
    
    used = osutils.du(discpath)
    for rpmnvra in order:
      if not packages.has_key(rpmnvra): continue
      
      for file in packages[rpmnvra]:
        size = osutils.du(join(pkgdir, file))
        assert size > 0
        newsize = used + size
        
        if disc == 1: maxsize = self.discsize - self.comps - self.reserve
        else:         maxsize = self.discsize
        
        if newsize > maxsize:
          # move to the next disc
          try:
            nextdisc = self.rpm_disc_map.index(disc+1)
            disc = self.rpm_disc_map[nextdisc]
            discpath = join(self.split_tree, '%s-disc%d' % (self.product, disc))
            self.link(pkgdir, join(discpath, self.product), [file])
          except (IndexError, ValueError):
            disc = disc - 1
            print 'DEBUG: overflow from disc %d onto disc %d' % (disc+1, disc)
            print 'DEBUG: newsize: %s maxsize: %s' % (newsize, maxsize)
            continue
        else:
          self.link(pkgdir, join(discpath, self.product), [file])
      used = newsize
  
  def split_srpms(self):
    if not self.dosrc:
      return
    
    srpms = []
    # create list of (size, srpm) tuples
    for srpm in osutils.find(self.unified_source_tree, name='*.[Ss][Rr][Cc].[Rr][Pp][Mm]'):
      size = os.path.getsize(join(self.unified_source_tree, srpm))
      srpms.append((size, srpm))
    
    srpms.sort()
    srpms.reverse()
    
    # keep list of SRPM trees and their sizes
    sizes = []
    for disc in self.srpm_disc_map:
      sizes.append([osutils.du(join(self.split_tree, '%s-disc%d' % (self.product, disc))), disc])
    sizes.sort()
    
    # add srpm to the smallest source tree
    for srpmtup in srpms:
      os.link(join(self.unified_source_tree, srpmtup[1]),
              join(self.split_tree, '%s-disc%d/SRPMS/%s' % \
                (self.product, sizes[0][1], osutils.basename(srpmtup[1]))))
      sizes[0][0] += srpmtup[0]
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
