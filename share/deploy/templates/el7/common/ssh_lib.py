#!/usr/bin/python

import subprocess
import sys

from deploy.util import pps

def create_keys(dir, user=None):
  seckey = pps.path('%s/id_rsa' % dir)
  pubkey = pps.path('%s/id_rsa.pub' % dir)

  if (not seckey.exists() or
      not pubkey.exists() or
      (user and 
       len(seckey.read_text().split()) == 3 and
       seckey.read_text().split()[2] != user)):

    # create key
    seckey.dirname.mkdirs(mode=0700)
    seckey.rm(force=True)
    pubkey.rm(force=True)
    r = subprocess.call('ssh-keygen -q -t rsa -b 2048 -N "" -f %s' % seckey,
                        shell=True)
    if r != 0:
      sys.exit(r)

    # replace user
    if user:
      cols = pubkey.read_text().split()
      cols[2] = user 
      pubkey.write_text(' '.join(cols) + '\n')
