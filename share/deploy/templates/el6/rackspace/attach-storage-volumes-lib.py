import ConfigParser
import os
import string
import subprocess
import sys
import time

import novaclient
import novaclient.auth_plugin
import novaclient.v1_1.client as nova_client

fqdn = "%{fqdn}"
ssh_host = "%{ssh-host}"
volume_data_file = "%{storage-data-file-%{module}}"

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
def get_server_id():
  return nova.servers.find(name=fqdn).id

def get_curr_volumes(server_id):
  return nova.volumes.get_server_volumes(server_id)

def write_config(section):
  with open(volume_data_file, "a") as f:
    f.write(section)

def read_config():
  # read config
  config = ConfigParser.SafeConfigParser() 
  config.read(volume_data_file)

  # validate config
  # note - we require a device name rather than allowing rackspace to auto
  # select one because later scripts that run on the client system (partition,
  # format, mount) need to know the device name, and it is easy to share
  # between scripts using a macro
  required_opts = ['size', 'device', 'mountpoint']
  for s in config.sections():
    for opt in required_opts:
      if opt not in config.options(s):
        sys.stderr.write("Required option '%s' not specified for storage "
                         "volume '%s'" % (opt, s))
        sys.exit(1)

    # disallow device names from /dev/xvdq onward as these fail without error
    device = config.get(s, 'device')
    valid_chars = string.ascii_lowercase[1:16]
    if not (device.startswith('/dev/xvd') and device[-1] in valid_chars):
      sys.stderr.write("Invalid device name '%s'. Device names must start "
                       "with '/dev/xvd' and end with a letter between 'b' and "
                       "'p', e.g. '/dev/xvdb'." % device)
      sys.exit(1)


  # write missing options to file so that mount-storage-volumes-lib.py
  # can simply read the file (after it has been copied using
  # copy_config_to_client) without setting defaults, validating, etc.
  for s in config.sections():
    try:
      config.get(s, 'format')
    except ConfigParser.NoOptionError:
      config.set(s, 'format', 'ext3')

    try:
      config.get(s, 'type')
    except ConfigParser.NoOptionError:
      config.set(s, 'type', 'SATA')

  with open(volume_data_file, 'wb') as f:
    config.write(f)

  return config

def copy_config_to_client():
  opts = ("-o StrictHostKeyChecking=no ")
  r = subprocess.call('scp %(opts)s  %(file)s %(host)s:%(file)s' % 
                     {'opts': opts,
                      'file': volume_data_file, 
                      'host': ssh_host},
                      shell=True)
  if r != 0:
    sys.stderr.write("Error copying %s to %s" % (volume_data_file, ssh_host))
    sys.exit(1)
  
def create_volume():
  volumes = nova_volume.volumes.findall(display_name=name)

  if len(volumes) == 0: # create volume
    volume = nova_volume.volumes.create(size=config.get(name, 'size'), 
                                        display_name = name,
                                        volume_type=config.get(name, 'type'))

  elif len(volumes) == 1: # use existing volume
    volume = volumes[0]

  elif len(volumes) > 1: # multiple volumes - raise error
    sys.stderr.write("Multiple volumes found with the name '%s'. Delete or "                         "rename unwanted volumes and try again." % name)
    sys.exit(1)

  return volume.id

def attach_volume(server_id, volume_id):
  # note - create_server_volume fails without error on device names q and above,
  # e.g. /dev/xvdp works, /dev/xvdq does not
  device = config.get(name, 'device')
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
      if nova_volume.volumes.get(volume_id).status == "in-use": 
        break
      else: 
        print ("attaching '%s' volume at '%s'... %s seconds" % 
              (name, device, seconds))
        seconds += 2
        time.sleep(2)

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
            (name, device, seconds))
      seconds += 2
      time.sleep(2)


