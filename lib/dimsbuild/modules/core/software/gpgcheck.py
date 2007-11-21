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
  def __init__(self, logger, relpath, repo):
    self.logger = logger
    self.relpath = relpath
    self.repo = repo

  def sync_start(self):
    self.logger.log(1, L1("downloading gpgkeys - '%s'" % self.repo))

class GpgCheckEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'gpgcheck',
      version = '0',
      requires = ['rpms-by-repoid', 'repos'],
    )

    self.DATA = {
      'variables': [],
      'input':     [],
      'output':    [],
    }

  def setup(self):
    self.diff.setup(self.DATA)

    self.gpgkeys = {}  # keys to download
    self.rpms = {}    # rpms to check

    for repo in self.cvars['repos'].values():
      if self.cvars['rpms-by-repoid'].has_key(repo.id) and \
         repo.has_key('gpgcheck') and repo['gpgcheck'] in BOOLEANS_TRUE:
        if repo.gpgkeys:
          self.gpgkeys[repo.id] = repo.gpgkeys
          self.rpms[repo.id] = self.cvars['rpms-by-repoid'][repo.id]
        else:
          raise RuntimeError("GPGcheck enabled for '%s' repository, but no keys "
          "provided." % repo.id)

    for repo in self.gpgkeys.keys():
      self.io.setup_sync(self.mddir/repo, paths=self.gpgkeys[repo], id=repo)
    self.DATA['variables'].append('rpms')
    self.DATA['variables'].append('gpgkeys')

  def run(self):
    if not self.rpms:
      self.io.clean_eventcache(all=True) # remove old keys
      self.diff.write_metadata()
      return

    for repo in sorted(self.rpms.keys()):
      newrpms = []
      homedir = self.mddir/repo/'homedir'
      self.DATA['output'].append(homedir)
      self.io.sync_input(cache=True, what=repo,
                         cb=GPGFilesCallback(self.logger, self.mddir, repo))

      # if gpgkeys have changed for this repo, (re)create homedir and
      # add all rpms from the repo to check list
      if self.diff.handlers['variables'].diffdict.has_key('gpgkeys'):
        md, curr = self.diff.handlers['variables'].diffdict['gpgkeys']
        if not hasattr(md, '__iter__') or not md.has_key(repo):
          md = {repo: []}
        if set(curr[repo]).difference(set(md[repo])):
          newrpms = self.rpms[repo]
          homedir.rm(force=True, recursive=True)
          homedir.mkdirs()
          for key in self.io.list_output(what=repo):
            shlib.execute('gpg --homedir %s --import %s' %(homedir,key))

      # if new rpms have been added from this repo, add them to check list
      else:
        if self.diff.handlers['variables'].diffdict.has_key('rpms'):
          md, curr = self.diff.handlers['variables'].diffdict['rpms']
          if not hasattr(md, '__iter__'): md = {}
          if md.has_key(repo):
            newrpms = sorted(set(curr[repo]).difference(set(md[repo])))

      # if we found rpms to check in the above tests, check them now
      if newrpms:
        invalids = []
        self.log(1, L1("checking rpms - '%s'" % repo))
        for rpm in newrpms:
          try:
            self.log(2, L2(rpm.basename+' '), newline=False, format='%(message)-70.70s')
            mkrpm.VerifyRpm(rpm, homedir=homedir)
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
