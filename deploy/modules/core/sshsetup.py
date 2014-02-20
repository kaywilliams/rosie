#
# Copyright (c) 2013
# Deploy Foundation. All rights reserved.
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
from deploy.event      import Event
from deploy.errors     import DeployEventError
from deploy.dlogging   import L1
from deploy.util       import pps
from deploy.util       import shlib

def get_module_info(ptr, *args, **kwargs):
  return dict(
    api         = 5.0,
    events      = ['SshSetupEvent'],
    description = 'configures ssh for build machine root user'
  )

class SshSetupEvent(Event):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'sshsetup',
      parentid = 'setup-events',
      ptr = ptr,
      provides = ['sshsetup'],
      suppress_run_message = True,
      conditional = True, #don't run unless required by a deployment module
    )

  def setup(self):
    sshdir = pps.path('/root/.ssh')
    keyfile = sshdir / 'id_rsa'

    if not keyfile.exists():
      # generate keys
      try:
        self.log(1, L1("ssh key not found, generating"))
        cmd = '/usr/bin/ssh-keygen -t rsa -f %s -N ""' % keyfile 
        shlib.execute(cmd)
      except shlib.ShExecError, e:
        message = ("Error occurred creating ssh keys for the "
                   "root user. The error was: %s\n"
                   "If the error persists, you can generate keys manually "
                   "using the command\n '%s'" % (e, cmd))
        raise KeyGenerationFailed(message=message)
      # add to ssh agent, ignoring errors as the agent may not be installed
      try:
        shlib.execute('/usr/bin/ssh-add')
      except shlib.ShExecError:
        pass

    # enable ssh to local machine
    authkeys = sshdir / 'authorized_keys'
    if not authkeys.exists(): authkeys.touch()
    authkeys.chmod(0600)

    pubkey = (keyfile + '.pub').read_text()
    if not pubkey in authkeys.read_text():
      authkeys.write_text(authkeys.read_text() + pubkey)
    
    self._config.resolve_macros(map={'%{build-host-pubkey}': 
                                     (keyfile + '.pub').read_text()})

class KeyGenerationFailed(DeployEventError):
  message = "%(message)s"
