import re
import stat

from rpmUtils.arch import getArchList

from dims import shlib
from dims import pps

from dimsbuild.constants import RPM_PNVRA
from dimsbuild.event     import Event, RepoMixin #!

API_VERSION = 5.0

P = pps.Path

RPM_PNVRA_REGEX = re.compile(RPM_PNVRA)

class DownloadEvent(Event, RepoMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'download',
      provides = ['input-rpms', 'cached-rpms'],
      requires = ['pkglist', 'repos'],
    )

    self._validarchs = getArchList(self.arch)
    
    self.DATA = {
      'variables': ['cvars[\'pkglist\']'],
      'input':     [],
      'output':    [],
    }
    
    self.builddata_dest = self.mddir/'rpms'
  
  def setup(self):
    self.setup_diff(self.DATA)
 
    self.input_rpms = set()  
    for repo in self.getAllRepos():
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        _,n,v,r,a = self._deformat(rpm)
        nvr = '%s-%s-%s' % (n,v,r)
        if nvr in self.cvars['pkglist'] and a in self._validarchs:
          rpm = P(rpminfo['file'])
          if isinstance(rpm, pps.path.http.HttpPath): #! bad        
            rpm._update_stat({'st_size':  rpminfo['size'],
                              'st_mtime': rpminfo['mtime'],
                              'st_mode':  stat.S_IFREG})
          self.input_rpms.add(rpm)

    self.setup_sync(self.builddata_dest, paths=self.input_rpms)
 
  def run(self):
    self.log(0, "running download")

    self.remove_output()
    self.sync_input()
    self.write_metadata()
    
  def apply(self):
    self.cvars['input-rpms'] = self.input_rpms
    self.cvars['cached-rpms'] = self.list_output()
  
  def _deformat(self, rpm):
    """ 
    p[ath],n[ame],v[ersion],r[elease],a[rch] = _deformat(rpm)
    
    Takes an rpm with an optional path prefix and splits it into its component parts.
    Returns a path, name, version, release, arch tuple.
    """
    try:
      return RPM_PNVRA_REGEX.match(rpm).groups()
    except (AttributeError, IndexError), e:
      self.errlog(2, "DEBUG: Unable to extract rpm information from name '%s'" % rpm)
      return (None, None, None, None, None)


EVENTS = {'SOFTWARE': [DownloadEvent]}

#------ ERRORS ------#
class RpmSignatureInvalidError(StandardError):
  "Class of exceptions raised when an RPM signature check fails in some way"
