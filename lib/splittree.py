import copy
import os
import re
import rpm

from math import ceil
from os.path import exists, isfile, isdir, join

import dims.FormattedFile as ffile
import dims.pkgorder      as pkgorder
import dims.osutils       as osutils

TS = rpm.TransactionSet()
TS.setVSFlags(-1)

SIZE_REGEX = re.compile('[\s]*([\d]+(?:\.[\d]+)?)[\s]*([kKmMgG]?)[bB]?[\s]*$')

SIZE_CD  = '640MB'
SIZE_DVD = '4.7GB'

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
    
    self.total_discs = None
    self.rpm_discs = None
    self.srpm_discs = None
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
    size_total = osutils.du(self.unified_tree)
    size_rpms = osutils.du(osutils.find(join(self.unified_tree, self.product),
                                        name='*.[Rr][Pp][Mm]'))
    if self.dosrc:
      size_srpms = osutils.du(osutils.find(self.unified_source_tree,
                                           name='*.[Ss][Rr][Cc].[Rr][Pp][Mm]'))
    else:
      size_srpms = 0
    
    size_extras = size_total - size_rpms - size_srpms
    
    self.total_discs = int(ceil(float(size_total)/self.discsize))
    self.rpm_discs = self.__consume_discs(size_rpms+size_extras)
    if self.dosrc:
      self.srpm_discs = self.__consume_discs(size_srpms)
      self.total_discs += 1
    else:
      self.srmp_discs = 0
    
    # lists mapping rpms and srpms to discs
    self.rpm_disc_map   = range(1, self.rpm_discs + 1)
    self.srpm_disc_map  = range(self.total_discs - (self.srpm_discs or 0) + 1, self.total_discs + 1)
  
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
        filelist = osutils.find(self.unified_tree, type=osutils.TYPE_FILE,
                                nregex='.*(\.discinfo|.*\.[Rr][Pp][Mm]).*', prefix=False)
        dirlist  = osutils.find(self.unified_tree, type=osutils.TYPE_DIR,
                                nregex='.*(RPMS|SRPMS|%s).*' % self.product, prefix=False)
        
        for dir in dirlist:
          osutils.mkdir(join(discpath, dir), parent=True)
        
        for file in filelist:
          osutils.cp(join(self.unified_tree, file), join(discpath, file), link=True)
        
      else:
        self.link(self.unified_tree, discpath, self.common_files)
      self.create_discinfo(i)
    
    if self.srpm_discs != 0:
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
      pkgnvr = nvra(join(pkgdir, rpm))
      
      if packages.has_key(pkgnvr):
        packages[pkgnvr].append(rpm)
      else:
        packages[pkgnvr] = [rpm]
    
    order = pkgorder.parse_pkgorder(self.pkgorder)
    for i in range(0, len(order)):
      order[i] = pkgtup_to_nvra(order[i])
    
    disc = self.rpm_disc_map[0]
    discpath = join(self.split_tree, '%s-disc%d' % (self.product, disc))
    
    for rpmnvr in order:
      if not packages.has_key(rpmnvr): continue
      for file in packages[rpmnvr]:
        used = osutils.du(discpath)
        size = osutils.du(join(pkgdir, file))
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
          except IndexError:
            disc = disc - 1
            print 'DEBUG: overflow from disc %d onto disc %d' % (disc+1, disc)
            continue
        else:
          self.link(pkgdir, join(discpath, self.product), [file])
  
  def split_srpms(self):
    if self.srpm_discs is None:
      return
    
    srpms = []
    # create list of (size, srpm) tuples
    for srpm in osutils.find(self.unified_source_tree, name='*.[Ss][Rr][Cc].[Rr][Pp][Mm]'):
      size = os.path.getsize(join(self.unified_source_tree, srpm))
      srpms.append((size, srpm))
    
    srpms.sort()
    srpms.reverse()
    
    for srpmtup in srpms:
      for disc in self.srpm_disc_map:
        discpath = join(self.split_tree, '%s-disc%d' % (self.product, disc))
        cursize = osutils.du(discpath)
        if cursize > self.discsize:
          if len(self.srpm_disc_map) < 2:
            print 'DEBUG: overflow %s onto disc %d' % (srpmtup[1], disc)
            break
          else:
            self.srpm_disc_map.pop(self.srpm_disc_map.index(disc))
      
      os.link(join(self.unified_source_tree, srpmtup[1]),
              join(self.split_tree, '%s-disc%d/SRPMS/%s' % \
                (self.product, self.get_smallest_tree(), osutils.basename(srpmtup[1]))))
  
  def get_smallest_tree(self):
    sizes = []
    for disc in self.srpm_disc_map:
      sizes.append((osutils.du(join(self.split_tree, '%s-disc%d' % (self.product, disc))), disc))
    sizes.sort()
    return sizes[0][1]

def nvra(pkgfile):
  fd = os.open(pkgfile, os.O_RDONLY)
  h = TS.hdrFromFdno(fd)
  os.close(fd)
  return '%s-%s-%s' % (h['name'], h['version'], h['release'])

def pkgtup_to_nvra(pkgtup):
  return '%s-%s-%s' % (pkgtup[0], pkgtup[3], pkgtup[4])

def parse_size(size):
  if type(size) == type(0):
    pass
  elif type(size) == type(0.0):
    return int(size)
  elif type(size) == type(''):
    if   size.upper() == 'CD':  size = SIZE_CD
    elif size.upper() == 'DVD': size = SIZE_DVD
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
