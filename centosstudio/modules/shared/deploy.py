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
from centosstudio.util import pps
from centosstudio.util import sshlib 

from UserDict import DictMixin

SSH_RETRIES = 24
SSH_SLEEP = 5

class DeployEventMixin:
  deploy_mixin_version = "1.02"

  def __init__(self, *args, **kwargs):
    self.requires.add('%s-setup-options' % self.moduleid,)
    self.conditionally_requires.update(['rpmbuild-data', 'release-rpm',
                                        'config-rpms'])

    # we're doing this in init rather than in validate (where it 
    # should technically be) so that if no scripts are present
    # (i.e. scripts_provided is False) parent events can disable themselves.

    # set up script default parameters
    self.scripts = {
      'trigger':      dict( ssh=True, activate=True, connect=True),
      'activate':     dict( ssh=False,),
      'install':      dict( ssh=False),
      'post-install': dict( ssh=True),
      'post':         dict( ssh=True)}

    # update scripts dict using config and validate script attributes
    self.scripts_provided = False
    for script in self.scripts:
      if self.config.getxpath(script, None) is not None: 
        # update enabled attribute
        self.scripts[script]['enabled'] = True
        self.scripts_provided = True

        # special processing for trigger element 
        if script == 'trigger':
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
    # todo - share this with srpmbuild
    self.ssh = dict(
      enabled      = self.cvars[self.cvar_root]['ssh'],
      hostname     = self.cvars[self.cvar_root]['hostname'],
      key_filename = str(self.cvars[self.cvar_root]['ssh-secfile']),
      port         = 22,
      username     = 'root',
      )

    for key in self.ssh:
      self.DATA['config'].append('@%s' % key)

    # setup scripts - do this before trigger macro resolution
    self.all_scripts = {} 
    for script in self.scripts:
      if self.scripts[script].setdefault('enabled', False):
        self.scripts[script]['script-ids'] = []
        self.scripts[script]['ssh-values'] = []

        scripts = self.config.xpath('%s/script' % script)
        for subscript in scripts:
          id = '%s' % subscript.getxpath('@id', '%s' % script)
          # ensure no duplicate ids
          xpath = self._configtree.getpath(subscript)
          csum = self._get_script_csum(xpath)
          index = 1
          while id in self.all_scripts and self.all_scripts[id][1] != csum:
            id = id + str(index)
            index += 1
          self.all_scripts[id] = [xpath, csum ] 

          self.scripts[script]['script-ids'].append(id)
          self.scripts[script]['ssh-values'].append(subscript.getbool('@ssh', 
                                             self.scripts[script]['ssh']))


    # resolve trigger macros 
    trigger_data = { 
      'release_rpm':         self._get_rpm_csum('release-rpm'),
      'config_rpms':         self._get_rpm_csum('config-rpms'),
      'kickstart':           self._get_csum(self.kstext),
      'treeinfo':            self._get_csum(self.cvars['base-treeinfo-text']),
      'install_scripts':     self._get_script_csum('install/script'),
      'post_install_scripts':self._get_script_csum('post-install/script'),
      }

    for key in trigger_data: 
      self.config.resolve_macros('.' , {'%%{%s}' % key: trigger_data[key]})

    triggers = self.config.getxpath('trigger/@triggers', '')
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
      triggers = getattr(self, 'default_install_triggers', [])

    triggers.sort()
    self.config.resolve_macros('.', {'%{triggers}': ' '.join(triggers)})

    # add data for active triggers to diff variables
    self.active_triggers = [ (x, trigger_data) for x in triggers ]
    self.DATA['variables'].append('active_triggers')

    self.deploydir = self.LIB_DIR / 'deploy'
    self.triggerfile = self.deploydir / 'trigger_info' # match script varname
    self.config.resolve_macros('.', {'%{trigger-file}': self.triggerfile})


    # setup to create script files - do this after macro resolution
    for id in self.all_scripts:
      self.io.add_xpath(self.all_scripts[id][0], self.mddir, destname=id, 
                        id=id, mode='750', content='text')

  def run(self):
    for id in self.all_scripts:
      self.io.process_files(what=id)

    self.do_clean=True # clean the deploydir once per session

    if self._reinstall():
      self.cvars['%s-reinstalled' % self.moduleid] = True # used by test cases
      if hasattr(self, 'test_fail_on_reinstall'): #set by test cases
        raise CentOSStudioError('test fail on reinstall')
      self._execute('install')
      self._execute('activate')
      self._execute('post-install')
      self._execute('post')

    else:
      self._execute('activate')
      self._execute('post')
 
 
  #------ Helper Functions ------#
  def _get_csum(self, text):
    return hashlib.md5(text).hexdigest()

  def _get_rpm_csum(self, id):
    if not 'rpmbuild-data' in self.cvars or not self.cvars[id]:
      return self._get_csum('')
    rpms = self.cvars[id]
    if isinstance(rpms, basestring):
      rpms = [ rpms ]
    releases = []
    for rpm in rpms:
      releases.append(self.cvars['rpmbuild-data'][rpm]['rpm-release'])
    if releases:
      releases.sort()
      return self._get_csum(''.join(releases)) # simple way to determine if
                                               # any release numbers have
                                               # changed
    else:
      return self._get_csum('')

  def _get_script_csum(self, xpath):
    text = ''
    for script in self.config.xpath(xpath, []):
      text = text + script.getxpath('text()', '')
    return self._get_csum(text) 

  def _reinstall(self):
    if not self.scripts['install']['enabled']:
      return False # don't try to install since we haven't got a script

    # can we activate the machine?
    if self.scripts['trigger']['activate']:
      try:
        self._execute('activate')
      except (ScriptFailedError, SSHScriptFailedError), e:
        self.log(3, L0(e))
        self.log(1, L1("unable to activate machine, reinstalling..."))
        return True # reinstall

    # can we get an ssh connection?
    if (self.ssh['enabled'] is True and 
        self.scripts['trigger']['connect']):
      params = SSHParameters(self, 'trigger')
      self.log(1, L1('attempting to connect'))
      try:
        client = self._ssh_connect(params)
        client.close()
      except SSHFailedError, e:
        self.log(3, L1(e))
        self.log(1, L1("unable to connect to machine, reinstalling...")) 
        return True # reinstall

    # does the trigger script return success?
    if self.scripts['trigger']['enabled']:
      try:
        self._execute('trigger')
      except ScriptFailedError, e:
        self.log(3, L1(str(e)))
        self.log(1, L1("trigger script failed, reinstalling..."))
        return True # reinstall

    # everything looks good
    return False # don't reinstall
  
  def _execute(self, script):
    if not self.scripts[script]['enabled']: return

    ids = self.scripts[script]['script-ids']
    for id in ids:
      cmd = self.io.list_output(what=id)[0]
      verbose = self.config.getbool('%s/script[@id="%s"]/@verbose' % 
                                   (script, id), False)
      self.log(1, L1('running %s script' % id))

      if (self.ssh['enabled'] and 
          self.scripts[script]['ssh-values'][ids.index(id)]):
        # run cmd on remote machine
        params = SSHParameters(self, script)
        try:
          try:
            client = self._ssh_connect(params)
          except SSHFailedError, e:
            raise SSHScriptFailedError(id=id, host=params['hostname'], 
                                       message=str(e))

          # create sftp client
          sftp = paramiko.SFTPClient.from_transport(client.get_transport())

          # create libdir
          if not self.LIB_DIR.basename in sftp.listdir(str(
                                          self.LIB_DIR.dirname)):
            sftp.mkdir(str(self.LIB_DIR))

          # create deploydir
          if not (self.deploydir.basename in 
                  sftp.listdir(str(self.deploydir.dirname))): 
            sftp.mkdir(str(self.deploydir))
            sftp.chmod(str(self.deploydir), mode=0750)

          # clean deploydir - except for trigger file
          if self.do_clean:
            files = sftp.listdir(str(self.deploydir))
            if self.triggerfile.basename in files:
              files.remove(str(self.triggerfile.basename))
            for f in files:
              sftp.remove(str(self.deploydir/f))
            self.do_clean = False # only clean once per session

          # copy script
          sftp.put(cmd, str( self.deploydir/cmd.basename )) # cmd is local file 
          sftp.chmod(str(self.deploydir/cmd.basename), mode=0750)
 
          # execute script
          cmd = str(self.deploydir/cmd.basename) # now cmd is remote file
          try:
            self._ssh_execute(client, cmd, verbose)
          except SSHFailedError, e:
            raise SSHScriptFailedError(id=id, host=params['hostname'],
                                       message=str(e))
  
        finally:
          if 'client' in locals(): client.close()

      else: # run cmd on the local machine
        self._local_execute(cmd, verbose)

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

  def _ssh_execute(self, client, cmd, verbose=False, log_format='L2'):
    self.log(2, eval('%s' % log_format)("executing \'%s\' on host" % cmd))
    chan = client.get_transport().open_session()
    chan.exec_command('"%s"' % cmd)

    outlines = []
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
            outlines.extend(data.rstrip('\n').split('\n'))
            if verbose or self.logger.test(4):
              if header_logged is False:
                self.logger.log_header(0, "%s event - '%s' script output" % 
                                      (self.id, pps.path(cmd).basename))
                header_logged = True
              self.log(0, data.rstrip('\n'))
        if chan.recv_stderr_ready():
          data = chan.recv_stderr(1024)
          if data:
            got_data = True
            errlines.extend(data.rstrip('\n').split('\n'))
        if not got_data:
          break

    if header_logged:
      self.logger.log(0, "%s" % '=' * MSG_MAXWIDTH)
      self.logger.log(0, '')
      
    status = chan.recv_exit_status()
    chan.close()

    if status != 0:
      raise SSHFailedError(message='\n'.join(outlines + errlines))

  def _local_execute(self, cmd, verbose=False):
      proc = subprocess.Popen('"%s"' % cmd, shell=True, 
                                            stdout=subprocess.PIPE, 
                                            stderr=subprocess.PIPE)

      errlines = []
      header_logged = False
      while True:
        outline = proc.stdout.readline().rstrip()
        errline = proc.stderr.readline().rstrip()
        if outline != '' or errline != '' or proc.poll() is None:
          if outline and (verbose or self.logger.test(4)): 
            if not header_logged:
              self.logger.log_header(0, "%s event - '%s' script output" %
                                    (self.id, pps.path(cmd).basename))
              header_logged = True
            self.log(0, outline)
          if errline: errlines.append(errline) 
        else:
          break

      if header_logged:
        self.logger.log(0, "%s" % '=' * MSG_MAXWIDTH)

      if proc.returncode != 0:
        raise ScriptFailedError(cmd=cmd, errtxt='\n'.join(errlines))
      return


class SSHParameters(DictMixin):
  def __init__(self, ptr, script):
    self.params = {}
    for param,value in ptr.ssh.items():
      if not param == 'enabled':
        self.params[param] = ptr.config.getxpath(
                             '%s/@%s' % (script, param), value)
    self.params['hostname'] = self.params['hostname'].replace('$id',
                              ptr.repoid)

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
  message = "Error occured running '%(cmd)s'. See error message below:\n %(errtxt)s"

class SSHFailedError(ScriptFailedError):
  message = "%(message)s"

class SSHScriptFailedError(ScriptFailedError):
  message = """Error(s) occured running '%(id)s' script on '%(host)s':
%(message)s"""

#------ Callbacks ------#
class SSHConnectCallback:
  def __init__(self, logger):
    self.logger = logger

  def start(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))

  def retry(self, message, *args, **kwargs):
    self.logger.log(2, L2(message))
