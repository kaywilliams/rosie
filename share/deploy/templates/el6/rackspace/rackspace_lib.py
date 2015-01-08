import ConfigParser
import os
import re
import string
import subprocess
import sys
import time

import novaclient
import novaclient.auth_plugin
import novaclient.v1_1.client as nova_client

SSH_OPTS = ("-o BatchMode=yes "
            "-o UserKnownHostsFile=%{ssh-host-key-file}")

# read authfile
d={}
with open("/root/rackspace/rackspace_admin", 'r') as authfile:
  for line in authfile.readlines():
     k,v = line.strip().replace('export ', '').split('=')
     d[k] = v
auth_plugin = novaclient.auth_plugin.load_plugin('rackspace')

# create nova client
nova = nova_client.Client(auth_url=d['OS_AUTH_URL'],
                       username=d['OS_USERNAME'],
                       api_key=d['OS_PASSWORD'],
                       project_id=d['OS_TENANT_NAME'],
                       region_name=d['OS_REGION_NAME'],
                       auth_system=d['OS_AUTH_SYSTEM'],
                       auth_plugin=auth_plugin)

# create nova_volume client
nova_volume = nova_client.Client(auth_url=d['OS_AUTH_URL'],
                       username=d['OS_USERNAME'],
                       api_key=d['OS_PASSWORD'],
                       project_id=d['OS_TENANT_NAME'],
                       region_name=d['OS_REGION_NAME'],
                       auth_system=d['OS_AUTH_SYSTEM'],
                       auth_plugin=auth_plugin,
                       service_type='volume')

##### helper functions #####
def clean_name(name):
  return re.sub(r'-publish$', '', name)

def get_server_id(fqdn):
  return nova.servers.find(name=fqdn).id

def get_curr_volumes(server_id):
  return nova.volumes.get_server_volumes(server_id)

def validate_device(device):
  # note - we require a device name rather than allowing rackspace to auto
  # select one because later scripts that run on the client system (partition,
  # format, mount) need to know the device name, and it is easy to share
  # between scripts using a macro

  # disallow device names from /dev/xvdq onward as these fail without error
  valid_chars = string.ascii_lowercase[1:16]
  if not (device.startswith('/dev/xvd') and device[-1] in valid_chars):
    sys.stderr.write("Invalid device name '%s'. Device names must start "
                     "with '/dev/xvd' and end with a letter between 'b' and "
                     "'p', e.g. '/dev/xvdb'.\n" % device)
    sys.exit(1)

def create_volume(name, size, type):
  name = clean_name(name) 
  volumes = nova_volume.volumes.findall(display_name=name)

  if len(volumes) == 0: # create volume
    volume = nova_volume.volumes.create(size=size, 
                                        display_name = name,
                                        volume_type=type)

  elif len(volumes) == 1: # use existing volume
    volume = volumes[0]

  elif len(volumes) > 1: # multiple volumes - raise error
    sys.stderr.write("Multiple volumes found with the name '%s'. Delete or "                         "rename unwanted volumes and try again.\n" % name)
    sys.exit(1)

  return volume.id

def attach_volume(server_id, volume_id, device, name, fqdn):
  name = clean_name(name)

  attach = False
  try:
    curr_device = nova.volumes.get_server_volume(server_id, volume_id).device
    if curr_device != device:
      detach_volume(server_id, volume_id)
      attach = True
  except novaclient.exceptions.NotFound:
    attach = True

  if attach:
    nova.volumes.create_server_volume(server_id, volume_id, device)

    # poll until attachment complete
    seconds = 0
    while True:
      status =  nova_volume.volumes.get(volume_id).status
      if status == "attaching": 
        print ("attaching '%s' volume at '%s'... %s seconds" % 
              (name, device, seconds))
        seconds += 2
        time.sleep(2)
      elif status == "in-use" and \
           device == nova.volumes.get_server_volume(
                          server_id, volume_id).device:
        break # attached
      else:
        sys.stderr.write("The volume '%s' did not attach to '%s'. The "
                         "current status is '%s'.\n" % (name, fqdn, status))
        sys.exit(1)

def detach_volume(server_id, volume_id):
  try:
    nova.volumes.delete_server_volume(server_id, volume_id)
  except novaclient.exceptions.NotFound:
    return

  # poll until volume is detached
  seconds = 0
  while True:
    if nova_volume.volumes.get(volume_id).status == 'available':
      break
    else:
      print ("detaching '%s' volume from '%s'... %s seconds" %
            (volume_id, device, seconds))
      seconds += 2
      time.sleep(2)

def delete_volume(volume_id):
  nova_volume.volumes.delete(volume_id)

  # poll until volume is deleted
  seconds = 0
  retry = 0
  while True:
    try:
      nova_volume.volumes.get(volume_id)
      print "deleting server... %s seconds" % seconds
  
      # retry delete every 30 seconds
      if retry >= 30:
        nova_volume.volumes.delete()
        retry = 0
  
      seconds += 5 
      retry += 5
      time.sleep(5)
    except novaclient.exceptions.NotFound:
      break

def attach(fqdn, name, size, type, device):
  name = clean_name(name)
  validate_device(device)
  server_id = get_server_id(fqdn)
  curr_volumes = get_curr_volumes(server_id)
  volume_id = create_volume(name, size, type)
  attach_volume(server_id, volume_id, device, name, fqdn)
