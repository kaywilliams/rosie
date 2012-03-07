#
# Copyright (c) 2012
# CentOS Solutions, Inc. All rights reserved.
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
import hashlib
import paramiko
import select
import signal
import subprocess 
import sys
import traceback

from centosstudio.cslogging import L0, L1, L2, MSG_MAXWIDTH
from centosstudio.errors import (CentOSStudioError, CentOSStudioEventError,
                                 SimpleCentOSStudioEventError)
from centosstudio.util import sshlib

from UserDict import DictMixin

SSH_RETRIES = 24
SSH_SLEEP = 5

class DeployEventMixin:
  deploy_mixin_version = "1.01"

  def __init__(self, *args, **kwargs):
    self.requires.add('%s-setup-options' % self.moduleid,)
    self.conditionally_requires.update(['rpmbuild-data', 'release-rpm-name'
                                        'config-rpm-name'])

    # we're doing this in init rather than in validate (where it 
    # should technically be) so that if no scripts are present
    # (i.e. scripts_provided is False) parent events can disable themselves.

    # set up script default parameters
    self.scripts = {
      'trigger-script': 
                       dict(message='running trigger install script',
                       ssh=True,
                       activate=True,
                       connect=True,
                       enabled = False),
      'activate-script': dict(message='running activate script',
                       ssh=False,
                       enabled = False),
      'delete-script': dict(message='running delete script',
                       enabled = False,
                       ssh=False),
      'install-script': dict(message='running install script',
                       enabled = False,
                       ssh=False),
      'post-install-script': 
                       dict(message='running post-install script',
                       enabled = False,
                       ssh=True),
      'update-script': dict(message='running update script',
                       enabled = False,
                       ssh=True),
      'post-script':   dict(message='running post script',
                       enabled = False,
                       ssh=True)}

    # update scripts dict using config and validate script attributes
    self.scripts_provided = False
    for script in self.scripts:
      if self.config.get(script, None) is not None: 
        # update enabled attribute
        self.scripts[script]['enabled'] = True
        self.scripts_provided = True

        # special processing for trigger-script
        if script == 'trigger-script':
          self.scripts[script]['activate'] = self.config.getbool(
            '%s/@activate-fails' % script, True)
          self.scripts[script]['connect'] = self.config.getbool(
            '%s/@ssh-connect-fails' % script, True)

  def setup(self): 
    # needs to be called after self.repomdfile and self.kstext are set
    self.cvar_root = '%s-setup-options' % self.moduleid

    # strip trailing whitespace from kstext so that diff testing works
    # as expected. using shelve for metadata storage (someday) will 
    # eliminate this issue
    try:
      self.kstext = self.kstext.rstrip()
    except:
      self.kstext = ''

    self.webpath = self.cvars[self.cvar_root]['webpath']

    self.DATA['variables'].extend(['webpath', 'kstext', 'deploy_mixin_version'])
    self.DATA['input'].append(self.repomdfile)

    # setup ssh values
    self.ssh = dict(
      enabled  =  self.cvars[self.cvar_root]['ssh'],
      hostname = self.cvars[self.cvar_root]['hostname'],
      port     = 22,
      username = 'root',
      password = self.cvars[self.cvar_root]['password'],
      )

    for key in self.ssh:
      self.DATA['config'].append('@%s' % key)

    # resolve trigger macros 
    trigger_data = {
      'release_rpm':         self._get_rpm_csum('release-rpm'),
      'config_rpm':          self._get_rpm_csum('config-rpm'),
      'kickstart':           self._get_csum(self.kstext),
      'treeinfo':            self._get_csum(self.cvars['base-treeinfo-text']),
      'install_script':      self._get_script_csum('install-script'),
      'post_install_script': self._get_script_csum('post-install-script'),
      }

    for key in trigger_data: 
      self.config.resolve_macros('.' , {'%%{%s}' % key: trigger_data[key]})

    triggers = self.config.get('trigger-script/@triggers', '')
    if triggers:
      triggers = [ s.strip() for s in triggers.replace(',', ' ').split() ]
      valids = [ s.replace('_', '-') for s in trigger_data.keys() ]
      invalids = set(triggers) - set(valids)
      if invalids:
        message = ("One or more trigger specified in the definition at '%s' "
                   "is invalid. The invalid values are '%s'. Available "
                   "values are '%s'." % ( self._config.file, 
                   "', '".join(invalids), "', '".join(valids)))
        raise InvalidInstallTriggerError(message=message)
    else:
      triggers = trigger_data.keys()

    triggers.sort()
    self.config.resolve_macros('.', {'%{triggers}': ' '.join(triggers)})

    self.deploydir = self.LIB_DIR / 'deploy'
    trigger_info = self.deploydir / 'trigger_info'
    self.config.resolve_macros('.', {'%s{trigger-file}': trigger_info})

    # setup scripts
    for script in self.scripts:
      if self.scripts[script]['enabled']:
        # setup script for processing
        self.io.add_xpath(script, self.mddir, destname=script, id=script, 
                          mode='750', content='text')


  def run(self):
    for script in self.scripts:
      self.io.process_files(what=script)

    if self._reinstall():
      self.cvars['%s-reinstalled' % self.moduleid] = True # used by test cases
      if hasattr(self, 'test_fail_on_reinstall'): #set by test cases
        raise CentOSStudioError('test fail on reinstall')
      self._execute('delete-script')
      self._execute('install-script')
      self._execute('activate-script')
      self._execute('post-install-script')
      self._execute('post-script')

    else:
      self._execute('activate-script')
      self._execute('update-script')
      self._execute('post-script')
 
 
  #------ Helper Functions ------#
  def _get_csum(self, text):
    return hashlib.md5(text).hexdigest()

  def _get_rpm_csum(self, rpmname):
    if not 'rpmbuild-data' in self.cvars:
      return self._get_csum('')
    data = self.cvars['rpmbuild-data'].get(self.cvars['%s-name' % rpmname], '')
    if data:
      return self._get_csum('%s-%s-%s.%s' % (data['rpm-name'], 
        data['rpm-version'], data['rpm-release'], data['rpm-arch']))
    else:
      return self._get_csum('')

  def _get_script_csum(self, scriptname):
    text = self.config.get('%s/text()' % scriptname, '')
    return self._get_csum(text) 

  def _reinstall(self):
    if not self.scripts['install-script']['enabled']:
      return False # don't try to install since we haven't got a script

    # can we activate the machine?
    if self.scripts['trigger-script']['activate']:
      try:
        self._execute('activate-script')
      except (ScriptFailedError, SSHScriptFailedError), e:
        self.log(3, L0(e))
        self.log(1, L1("unable to activate machine, reinstalling..."))
        return True # reinstall

    # can we get an ssh connection?
    if (self.ssh['enabled'] is True and 
        self.scripts['trigger-script']['connect']):
      params = SSHParameters(self, 'trigger-script')
      self.log(1, L1('attempting to connect'))
      try:
        client = self._ssh_connect(params)
        client.close()
      except (SSHFailedError), e:
        self.log(3, L1(e))
        self.log(1, L1("unable to connect to machine, reinstalling...")) 
        return True # reinstall

    # does the trigger script return success?
    if self.scripts['trigger-script']['enabled']:
      try:
        self._execute('trigger-script')
      except (ScriptFailedError), e:
        self.log(3, L1(e))
        self.log(1, L1("trigger-script failed, reinstalling..."))
        return True # reinstall

    # everything looks good
    return False # don't reinstall
  
  def _execute(self, script):
    if not self.io.list_output(script): return
    if 'message' in self.scripts[script]:
      self.log(1, L1(self.scripts[script]['message']))
    cmd = self.io.list_output(what=script)[0]

    if self.ssh['enabled'] and self.scripts[script]['ssh']: 
      # run cmd on remote machine
      params = SSHParameters(self, script)
      try:
        try:
          client = self._ssh_connect(params)
        except SSHFailedError, e:
          raise SSHScriptFailedError(script=script, message=str(e))

        # copy script to remote machine
        sftp = paramiko.SFTPClient.from_transport(client.get_transport())
        if not self.LIB_DIR.basename in sftp.listdir(str(self.LIB_DIR.dirname)):
          sftp.mkdir(str(self.LIB_DIR))
        if not (self.deploydir.basename in 
                sftp.listdir(str(self.deploydir.dirname))): 
          sftp.mkdir(str(self.deploydir))
          sftp.chmod(str(self.deploydir), mode=0750)
        sftp.put(self.io.list_output(what=script)[0], 
                 str(self.deploydir/script))
        sftp.chmod(str(self.deploydir/script), mode=0750)
 
        # execute script
        cmd = str(self.deploydir/script)
        try:
          self._ssh_execute(client, cmd)
        except SSHFailedError, e:
          raise SSHScriptFailedError(script=script, message=str(e))
  
      finally:
        if 'client' in locals(): client.close()

    else: # run cmd on the local machine
      self._local_execute(cmd)

  def _ssh_connect(self, params, log_format='L2'):
    try:
      try:
        self.log(2, eval('%s' % log_format)(
                         "connecting to host \'%s\'" % params['hostname'])) 
        signal.signal(signal.SIGINT, signal.default_int_handler) #enable ctrl+C
        client = sshlib.get_client(retries=SSH_RETRIES, sleep=SSH_SLEEP,
                                   callback=SSHConnectCallback(self.logger),
                                   **dict(params))

        # setting keepalive causes client to cancel processes started by the
        # server after the SSH session is terminated. It takes a few seconds for
        # the client to notice and cancel the process. 
        client.get_transport().set_keepalive(1)

      except sshlib.ConnectionFailedError, e:
        raise SSHFailedError(message=e) 

    except:
      if 'client' in locals(): client.close()
      raise

    return client

  def _ssh_execute(self, client, cmd, log_format='L2'):
    self.log(2, eval('%s' % log_format)("executing \'%s\' on host" % cmd))
    chan = client.get_transport().open_session()
    chan.exec_command(cmd)

    errlines = []
    header_logged = False
    while True:
      r, w, x = select.select([chan], [], [], 0.0)
      if len(r) > 0:
        got_data = False
        if chan.recv_ready():
          data = chan.recv(1024)
          if data:
            got_data = True
            if header_logged is False:
              self.logger.log_header(4, "%s event - '%s' output" % 
                                    (self.id, cmd))
              header_logged = True
            self.log(4, L0(data.rstrip('\n')))
        if chan.recv_stderr_ready():
          data = chan.recv_stderr(1024)
          if data:
            got_data = True
            errlines.extend(data.rstrip('\n').split('\n'))
        if not got_data:
          break

    if header_logged:
      self.logger.log(4, L0("%s" % '=' * MSG_MAXWIDTH))
      self.logger.log(4, L0(''))
      
    status = chan.recv_exit_status()
    chan.close()

    if status != 0:
      raise SSHFailedError(message='\n'.join(errlines))

  def _local_execute(self, cmd):
      proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                               stderr=subprocess.PIPE)

      errlines = []
      header_logged = False
      while True:
        outline = proc.stdout.readline().rstrip()
        errline = proc.stderr.readline().rstrip()
        if outline != '' or errline != '' or proc.poll() is None:
          if outline: 
            if not header_logged:
              self.logger.log_header(4, "%s event - '%s' output" %
                                    (self.id, cmd))
              header_logged = True
            self.log(4, L0(outline))
          if errline: errlines.append(errline) 
        else:
          break

      if header_logged:
        self.logger.log(4, L0("%s" % '=' * MSG_MAXWIDTH))

      if proc.returncode != 0:
        raise ScriptFailedError(script=cmd, errtxt='\n'.join(errlines))
      return


class SSHParameters(DictMixin):
  def __init__(self, ptr, script):
    self.params = {}
    for param,value in ptr.ssh.items():
      if not param == 'enabled':
        self.params[param] = ptr.config.get('%s/@%s' % (script, param), value)
    self.params['hostname'] = self.params['hostname'].replace('$id',
                              ptr.solutionid)

  def __getitem__(self, key):
    return self.params[key]
 
  def __setitem__(self, key, item):
    self.params[key] = item
 
  def __delitem__(self, key):
    self.params[key].clear()
 
  def keys(self):
    return self.params.keys()    

  def __str__(self):
    return ', '.join([ '%s=\'%s\'' % (k,self.params[k]) for k in self.params ])


#------ Errors ------#
class DeployMixinError(CentOSStudioEventError):
  message = "%(message)s"

class InvalidInstallTriggerError(DeployMixinError):
  message = "%(message)s"

class ScriptFailedError(DeployMixinError):
  message = "Error occured running '%(script)s'. See error message below:\n %(errtxt)s"

class SSHFailedError(ScriptFailedError):
  message = "%(message)s"

class SSHScriptFailedError(ScriptFailedError):
  message = """Error(s) occured running '%(script)s':
%(message)s"""

#------ Callbacks ------#
class SSHConnectCallback:
  def __init__(self, logger):
    self.logger = logger

  def start(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))

  def retry(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))
