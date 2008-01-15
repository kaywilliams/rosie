import copy

from rendition.xmllib import config

from spintest        import EventTestCase, ModuleTestSuite
from spintest.core   import make_extension_suite

class SourceReposEventTestCase(EventTestCase):
  moduleid = 'sources'
  eventid  = 'source-repos'
  def __init__(self, basedistro, conf=None):
    self._conf = _make_source_repos(basedistro)
    EventTestCase.__init__(self, basedistro, conf)

class SourcesEventTestCase(EventTestCase):
  moduleid = 'sources'
  eventid  = 'sources'
  def __init__(self, basedistro, conf=None):
    self._conf = _make_source_repos(basedistro)
    EventTestCase.__init__(self, basedistro, conf)

def make_suite(basedistro):
  suite = ModuleTestSuite('sources')

  suite.addTest(make_extension_suite(SourceReposEventTestCase, basedistro))
  suite.addTest(make_extension_suite(SourcesEventTestCase, basedistro))

  return suite

def _make_source_repos(distro):
  srcrepos = config.Element('sources')
  srcrepos.append(_make_repo('%s-base-source' % distro))
  return str(srcrepos) # hack, this has to be a string

def _make_repo(id, **kwargs):
  if id in SOURCE_REPOS.keys():
    d = copy.copy(SOURCE_REPOS[id]) # destructive
  else:
    d = {}

  d.update(kwargs)

  for k in ['baseurl']:
    if not d.has_key(k):
      raise ValueError("Missing key '%s' for repo '%s'" % (k, id))

  repo = config.Element('repo', attrs={'id': id})
  for k,v in d.items():
    config.Element(k, text=v, parent=repo)

  return repo

SOURCE_REPOS = {
  # fedora 6
  'fedora-6-base-source': {
    'name': 'fedora-6-base-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/core/6/source/SRPMS/'
  },
  'fedora-6-updates-source': {
    'name': 'fedora-6-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/core/updates/6/SRPMS/',
  },
  # fedora 7
  #'fedora-7-base-source': {
  #  'name': 'fedora-7-base-source',
  #  'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/releases/7/Fedora/source/SRPMS/',
  #},
  'fedora-7-base-source': {
    'name': 'fedora-7-base-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/releases/7/Everything/source/SRPMS/',
  },
  'fedora-7-updates-source': {
    'name': 'fedora-7-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/updates/7/SRPMS/',
  },
  # fedora 8
  #'fedora-8-base-source': {
  #  'name': 'fedora-8-base-source',
  #  'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/releases/8/Fedora/source/SRPMS/',
  #},
  'fedora-8-base-source': {
    'name': 'fedora-8-base-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/releases/8/Everything/source/SRPMS/',
  },
  'fedora-8-updates-source': {
    'name': 'fedora-8-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/fedora/updates/8/SRPMS/',
  },
  # redhat 5
  'redhat-5-base-source': {
    'name': 'redhat-5-base-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/redhat/5/os/SRPMS',
  },
  # centos 5
  'centos-5-base-source': {
    'name': 'centos-5-base-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/centos/5/os/SRPMS/',
  },
  'centos-5-updates-source': {
    'name': 'centos-5-updates-source',
    'baseurl': 'http://www.renditionsoftware.com/open_software/centos/5/updates/SRPMS/',
  },
}
