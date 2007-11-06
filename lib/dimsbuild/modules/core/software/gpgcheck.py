from dims import mkrpm
from dims import shlib
from dims import pps

from dimsbuild.event   import Event
from dimsbuild.logging import L1, L2
from dimsbuild.constants import BOOLEANS_TRUE
from dimsbuild.callback import FilesCallback

P = pps.Path

API_VERSION = 5.0
EVENTS = {'software': ['GpgCheckEvent']}

class GPGFilesCallback(FilesCallback):
  def sync_start(self):
    self.logger.log(1, L1("downloading gpgkeys"))

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      version = '1',
      requires = ['cached-rpms', 'repos'],
    )

    self.DATA = {
      'variables': [],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.keys = []   # gpgcheck keys to download
    self.checks = {} # rpms to check

    cached = {} # dictionary cached rpms by basename, fullname
    for rpm in self.cvars['cached-rpms']:
      cached[rpm.basename] = rpm

    for repo in self.cvars['repos'].values():
      rpms = []
      if repo.has_key('gpgcheck') and repo['gpgcheck'] in BOOLEANS_TRUE:
        self.keys.extend(repo.gpgkeys)
        for rpm in [ P(rpminfo['file']).basename for rpminfo in repo.repoinfo ]:
          if cached.has_key(rpm):
            rpms.append(cached[rpm])
      if rpms:
        self.checks[repo.id] = sorted(rpms)

    self.io.setup_sync(self.mddir, paths=self.keys, id='keys')
    self.DATA['variables'].append('checks')

  def run(self):
    if not self.checks:
      self.io.clean_eventcache(all=True) # remove old keys
      self.diff.write_metadata()
      return

    homedir = self.mddir/'homedir'
    self.DATA['output'].append(homedir)
    newkeys = self.io.sync_input(cache=True,
                                 cb=GPGFilesCallback(self.logger, self.mddir))

    if newkeys:
      newchecks = self.checks
      homedir.rm(force=True, recursive=True)
      homedir.mkdirs()
      for key in self.io.list_output(what='keys'):
        shlib.execute('gpg --homedir %s --import %s' %(homedir,key))
    else:
      md, curr = self.diff.handlers['variables'].diffdict['checks']
      if not hasattr(md, '__iter__'): md = {}
      newchecks = {}
      for repo in curr.keys():
        if md.has_key(repo):
          newrpms = sorted(set(curr[repo]).difference(set(md[repo])))
        if newrpms:
          newchecks[repo] = newrpms

    if newchecks:
      invalids = []
      for repo in newchecks.keys():
        self.log(1, L1("checking rpms from '%s' repository" % repo))
        for rpm in newchecks[repo]:
          try:
            self.log(2, L2(rpm.basename+' '), newline=False, format='%(message)-70.70s')
            mkrpm.VerifyRpm(rpm, homedir=homedir, force=True)
            self.logger.write(2, "OK\n")
          except mkrpm.RpmSignatureInvalidError:
            self.logger.write(2, "INVALID\n")
            invalids.append(rpm.basename)

      if invalids:
        raise RpmSignatureInvalidError("One or more RPMS failed "
                                       "GPG key checking: %s" % invalids)

    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()


#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
