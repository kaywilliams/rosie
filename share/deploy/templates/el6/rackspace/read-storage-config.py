import ConfigParser
import sys

def read_config():
  # read config
  config = ConfigParser.SafeConfigParser({ 
    'format': 'ext3',
    'type' :  'SATA',
    })
  config.read(volume_data_file)
  
  # validate config
  # note - we require a device name rather than allowing rackspace to auto
  # select one because later scripts that run on the client system (partition,
  # format, mount) need to know the device name, and it is easy to share
  # between scripts using a macro
  required_opts = ['size', 'device']
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

  return config
