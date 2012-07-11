#
# Copyright (c) 2012
# CentOS Studio Foundation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>
#
"""
shhlib.py

A basic library for establishing connections to remote machines over SSH
using Paramiko.
"""

import paramiko
import socket
import signal
import time

from decimal import Decimal

def get_client(retries=24, sleep=5, callback=None, **kwargs):
  """Create an ssh client object and establish a connection to the remote
  machine, waiting for a timeout period in case the system is starting. Accepts
  paramiko connection parameters as a dictionary (params). "Retries" specifies
  the number of time to retry the connection, and "sleep" specifies the time in 
  seconds to sleep between each retry. The defaults are 24 and 5, respectively,
  for a total wait period of 2 mintues. The callback parameter takes a callback
  object with two methods, start and retry. Start is called just after the first
  unsuccessful connect attempt.  Retry is called prior to each sleep session. 

  The get_client method returns a pointer to the client object. Also note that
  it ignores paramiko.BadHostKeyException, assuming that the host specified 
  in the parameters is the desired host, even if the underlying machine
  has changed since the prior connection.

  Callers should wrap this function and all related ssh/sftp actions in a 
  try/finally block with the finally block similar to the following:

  finally:
    if 'client' in locals(): client.close()
  """
  params = kwargs

  #establish connection
  cb = callback
  client = paramiko.SSHClient()
  client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
  for i in range(retries): # retry connect to host every 5 seconds for 2 minutes
    try:
      client.connect(**dict(params))
      break
    except (paramiko.AuthenticationException, 
            paramiko.BadAuthenticationType), e:
      raise ConnectionFailedError(str(e), params)
    except (socket.error, paramiko.SSHException), e:
      if i == 0:
        max = Decimal(retries) * sleep / 60
        if callback is not None:
          cb.start("Unable to connect. System may be starting. Will retry for %s minutes." % max, max=max)
      if callback is not None:
        cb.retry("%s. Retrying..." % e, error_obj = e)
      time.sleep(sleep)

    # host can change from installation to installation, so 
    # don't require a match to known hosts
    except paramiko.BadHostKeyException:
      pass

  else:
    raise ConnectionFailedError(str(e), params)

  return client

class ConnectionFailedError(Exception):
  def  __init__(self, message, params):
    self.hostname = params['hostname']
    self.message = message
    self.params = ', '.join([ '%s=\'%s\'' % (k,params[k]) 
                              for k in params ])

  def __str__(self):
    return ("Unable to establish connection with remote host: '%s':\n"
            "Error Message: %s\n"
            "SSH Parameters: %s" 
            % (self.hostname, self.message, self.params))
