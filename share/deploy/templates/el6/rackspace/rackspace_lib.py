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
    volume = nova_volume.volumes.create(size=int(size), 
                                        display_name = name,
                                        volume_type=type)

    # poll until volume is created 
    seconds = 0
    while True:
      volume = nova_volume.volumes.get(volume.id)
      if volume.status == 'available':
        break
      else:
        sys.stdout.write("creating volume '%s'... %s seconds" % (name, seconds))
        seconds += 2
        time.sleep(2)

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
    try:
      nova.volumes.create_server_volume(server_id, volume_id, device)
    except novaclient.exceptions.BadRequest, e:
      sys.stderr.write("Unable to attach volume '%s':\n\n%s" %s (name, e))
      sys.exit(1)

    # poll until attachment complete
    seconds = 0
    while True:
      status =  nova_volume.volumes.get(volume_id).status
      if status == "attaching": 
        sys.stdout.write("attaching '%s' volume at '%s'... %s seconds" % 
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

def delete_server(server, delete_volumes, ssh_host_key_file, ssh_host):
  # get server volumes
  server_volumes = nova.volumes.get_server_volumes(server.id)
  
  # unmount volumes
  unmount_volumes(server, server_volumes, ssh_host_key_file, ssh_host)
  
  # delete server
  _delete_server(server)
  
  # delete volumes
  if delete_volumes:
    for v in server_volumes:
      detach_volume(server.id, v)
      delete_volume(v)

def _delete_server(server):
  def log_deleting(seconds, task_state, status):
    sys.stdout.write("deleting... %s seconds (task state: %s, status: %s)\n"
                     % (seconds, task_state, status))
    seconds += 5 
    time.sleep(5)

    return seconds

  server.delete()
  
  # poll until server deleted
  seconds = 0
  while True:
    try:
      server = nova.servers.get(server.id)
      task_state = getattr(server, 'OS-EXT-STS:task_state')

      if str(server.status) == "ERROR":
        if hasattr(server, 'fault') and 'message' in server.fault:
          sys.stderr.write(server.fault['message'])
        else:
          sys.stderr.write("Unable to delete server '%s': task state is '%s' "
                           "and current status is '%s'."
                           % (server.name, task_state, server.status))
        sys.exit(1)

      if str(server.status) == "DELETED":
        # wait to exit until server has disappeared
        seconds = log_deleting(seconds, task_state, server.status)
        continue

      if task_state is None and str(server.status) == "ACTIVE":
        # wait as it takes a few seconds 1) for the task_state to register
        # deleting, and 2) for the server to disappear after deleted.
        seconds = log_deleting(seconds, task_state, server.status)
        continue

      if task_state != 'deleting':
        sys.stderr.write("Unable to delete server '%s': task state is '%s' "
                         "and current status is '%s'."
                         % (server.name, task_state, server.status))
        sys.exit(1)

      seconds = log_deleting(seconds, task_state, server.status)
  
    except novaclient.exceptions.NotFound:
      break

def unmount_volumes(server, server_volumes, ssh_host_key_file, ssh_host):
  # Note - unmounting volumes from a script that runs on localhost
  # since delete scripts can run before the ssh-client address is known
  #
  if server.status == 'ACTIVE':
    partitions = [ '%s1' % v.device for v in server_volumes ]
  
    opts = ("-o BatchMode=yes "
            "-o UserKnownHostsFile='%s' " 
            "-o ConnectTimeout=2") % ssh_host_key_file
  
    for v in server_volumes:
      partname = "%s1" % v.device
  
      # check if volume mounted
      cmd = "mount | grep -q '^%s '" % partname 
      r = subprocess.call('ssh %s %s %s' % (opts, ssh_host, cmd), shell='true')
      if r == 0:
        # unmount it
        cmd = "umount %s" % partname
        r = subprocess.call('ssh %s %s %s' % (opts, ssh_host, cmd), shell='true')
        if r != 0: # umount failed
          sys.stderr.write("\nError unmounting '%s' for volume id '%s'." %
                          (partname, v.id))
          sys.exit(r)

def detach_volume(server_id, volume_id):
  try:
    nova.volumes.delete_server_volume(server_id, volume_id)
  except novaclient.exceptions.NotFound:
    return

  # poll until volume is detached
  seconds = 0
  while True:
    volume = nova_volume.volumes.get(volume_id)
    if volume.status == 'available':
      break
    if volume.status == 'error_detaching':
      sys.stderr.write("error detaching '%s' volume" % volume_id)
      sys.exit(1)
    else:
      sys.stdout.write("detaching '%s' volume from '%s'... %s seconds" %
                      (volume_id, volume.device, seconds))
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
      sys.stdout.write("deleting server... %s seconds" % seconds)
  
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
