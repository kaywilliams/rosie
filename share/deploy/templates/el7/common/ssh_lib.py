#!/usr/bin/python

import subprocess
import sys

from deploy.util import pps

def create_keys(dir, user=None):
  seckey = pps.path('%s/id_rsa' % dir)
  pubkey = pps.path('%s/id_rsa.pub' % dir)

  # create key
  if not seckey.exists() or not pubkey.exists():
    seckey.dirname.mkdirs(mode=0700)
    seckey.rm(force=True)
    pubkey.rm(force=True)
    r = subprocess.call('ssh-keygen -q -t ecdsa -b 256 -N "" -f %s' % seckey,
                        shell=True)
    if r != 0:
      sys.exit(r)

  # replace user
  fields = pubkey.read_text().rstrip().split()
  if user:
    if len(fields) == 2:
      fields.append(user)
      pubkey.write_text(' '.join(fields) + '\n')
    if fields[2] != user:
      fields[2] = user
      pubkey.write_text(' '.join(fields) + '\n')
