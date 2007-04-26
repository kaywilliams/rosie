import csv
import os

from os.path import join, exists

import dims.listcompare as listcompare
import dims.osutils     as osutils
import dims.shlib       as shlib

from event     import EVENT_TYPE_MDLR
from interface import EventInterface

API_VERSION = 3.0

EVENTS = [
  {
    'id': 'manifest',
    'requires': ['MAIN'],
    'provides': ['manifest'],
    'parent': 'ALL',
  },
  {
    'id': 'iso',
    'requires': ['manifest'],
    'provides': ['iso'],
    'parent': 'ALL',
    'properties': EVENT_TYPE_MDLR,
  },
]

FIELDS = ['file', 'size', 'mtime']

def manifest_hook(interface):
  interface.setFlag('do-iso', False)
  manifest = []
  for file in osutils.tree(interface.getSoftwareStore(), prefix=False):
    manifest.append(__gen_manifest_line(join(interface.getSoftwareStore(), file)))
  
  mfile = join(interface.getMetadata(), 'manifest')
  if manifest_changed(manifest, mfile):
    interface.setFlag('do-iso', True)      
    if not exists(mfile): os.mknod(mfile)
    mf = open(mfile, 'w')
    mwriter = csv.DictWriter(mf, FIELDS, lineterminator='\n')
    for line in manifest:
      mwriter.writerow(line)
    mf.close()

def __gen_manifest_line(file):
  fstat = os.stat(file)
  return {'file': file,
          'size': str(fstat.st_size),
          'mtime': str(fstat.st_mtime)}

def manifest_changed(manifest, old_manifest_file):
  if exists(old_manifest_file):
    mf = open(old_manifest_file, 'r')
    mreader = csv.DictReader(mf, FIELDS)
    old_manifest = []
    for line in mreader: old_manifest.append(line)
    mf.close()
    
    return manifest != old_manifest
  else:
    return True

def iso_hook(interface):
  if not interface.getFlag('do-iso') and not interface.eventForceStatus('iso'):
    return
  interface.log(0, 'generating iso image(s)')
  isodir = join(osutils.dirname(interface.getSoftwareStore()), 'iso') # hack hack
  osutils.mkdir(isodir)
  os.chdir(isodir)
  
  # add -quiet and remove verbose when done testing
  shlib.execute('mkisofs -UJRTV "%s" -o %s.iso %s' % \
    ('%s %s %s' % (interface.product, interface.version, interface.release),
     interface.product,
     interface.getSoftwareStore()), verbose=True)
