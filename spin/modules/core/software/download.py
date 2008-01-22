import stat

from rpmUtils.arch import getArchList

from rendition import pps

from spin.constants import RPM_PNVRA_REGEX
from spin.event     import Event
from spin.logging   import L1, L2

API_VERSION = 5.0
EVENTS = {'software': ['DownloadEvent']}

P = pps.Path

class DownloadEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'download',
      provides = ['cached-rpms', 'rpms-by-repoid'],
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
    self.diff.setup(self.DATA)

    self.cvars['rpms-by-repoid'] = {}
    processed = []

    for repo in self.cvars['repos'].values():
      rpms = {}
      for rpminfo in repo.repoinfo:
        rpm = rpminfo['file']
        _,n,v,r,a = self._deformat(rpm)
        nvra = '%s-%s-%s.%s' % (n,v,r,a)
        if nvra in self.cvars['pkglist'] and nvra not in processed and \
             a in self._validarchs:
          rpm = P(rpm)
          if isinstance(rpm, pps.path.http.HttpPath): #! bad
            rpm._update_stat({'st_size':  rpminfo['size'],
                              'st_mtime': rpminfo['mtime'],
                              'st_mode':  (stat.S_IFREG | 0644)})
          rpms[rpm.basename] = rpm
          processed.append(nvra)
      self.io.add_fpaths(rpms.values(), self.builddata_dest, id=repo.id)
      if rpms:
        self.cvars['rpms-by-repoid'][repo.id] = \
          sorted([self.builddata_dest/rpm for rpm in rpms.keys()])

  def run(self):
    for repo in self.cvars['repos'].values():
      self.io.sync_input(link=True, cache=True, what=repo.id,
                         text=("downloading packages - '%s'" % repo.id))
    self.diff.write_metadata()

  def apply(self):
    self.io.clean_eventcache()
    self.cvars['cached-rpms'] = self.io.list_output()

  def _deformat(self, rpm):
    """
    p[ath],n[ame],v[ersion],r[elease],a[rch] = _deformat(rpm)

    Takes an rpm with an optional path prefix and splits it into its component parts.
    Returns a path, name, version, release, arch tuple.
    """
    try:
      return RPM_PNVRA_REGEX.match(rpm).groups()
    except (AttributeError, IndexError), e:
      self.log(2, L2("DEBUG: Unable to extract rpm information from name '%s'" % rpm))
      return (None, None, None, None, None)

  def error(self, e):
    # performing a subset of Event.error since sync handles partially downloaded files
    (self.mddir / 'debug').mkdir()
    if self.mdfile.exists():
      self.mdfile.rename(self.mddir/'debug'/self.mdfile.basename)
