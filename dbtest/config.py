"config.py - make a config 'file' for dimsbuild tests"

import copy

from StringIO import StringIO

from dims.xmllib import config

def make_repos(distro, repodefs=[]):
  "make a <repos> top level element with the base repo included"
  repos = config.Element('repos')
  repos.append(config.Element('base-repo', text='%s-base' % distro))
  for repo in repodefs:
    repos.append(repo)
  return repos

def make_main(eventid, **kwargs):
  "make a <main> top level element"
  main = config.Element('main')

  kwargs.setdefault('fullname', '%s event test' % eventid)
  kwargs.setdefault('product',  'test-%s' % eventid)
  kwargs.setdefault('version',  '0')

  for k,v in kwargs.items():
    config.Element(k, text=v, parent=main)
  return main

def make_default_config(eventid, basedistro='fedora-6'):
  "create a default config file"
  # make top level element
  distro = _make_distro()
  # make main element and append
  distro.append(make_main(eventid))
  # make repos element
  baserepo = _make_repo('%s-base' % basedistro)
  distro.append(make_repos(basedistro, [baserepo]))

  distro.file = '' # hack to get rpm building working

  return distro

def add_config_section(cfg, section):
  section = config.read(StringIO(section))
  for old in cfg.xpath(section.tag, []):
    cfg.remove(old)
  cfg.append(section)

def _make_distro():
  return config.Element('distro', attrs={'schema-version': '1.0'})

def _make_repo(id, **kwargs):
  "construct a repo, either from data in REPOS, below, or from kwargs"
  if id in REPOS.keys():
    d = copy.copy(REPOS[id])
  else:
    d = {}

  d.update(kwargs)

  for k in ['baseurl']: # make sure repo has all necessary/expected fields
    if not d.has_key(k):
      raise ValueError("Missing key '%s' for repo '%s'" % (k, id))

  repo = config.Element('repo', attrs={'id': id})
  for k,v in d.items():
    config.Element(k, text=v, parent=repo)

  return repo

REPOS = {
  # fedora 6
  'fedora-6-base': {
    'name': 'fedora-6-base',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/core/6/i386/os/',
  },
  'fedora-6-updates': {
    'name': 'fedora-6-updates',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/core/updates/6/i386/',
  },
  # fedora 7
  'fedora-7-base': {
    'name': 'fedora-7-base',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/releases/7/Fedora/i386/os/',
  },
  'fedora-7-updates': {
    'name': 'fedora-7-updates',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/updates/7/i386/',
  },
  'fedora-7-everything': {
    'name': 'fedora-7-everything',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/releases/7/Everything/i386/os/',
  },
  # fedora 8
  'fedora-8-base': {
    'name': 'fedora-8-base',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/releases/8/Fedora/i386/os/',
  },
  'fedora-8-updates': {
    'name': 'fedora-8-updates',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/updates/8/i386/',
  },
  'fedora-8-everything': {
    'name': 'fedora-8-everything',
    'baseurl': 'http://www.abodiosoftware.com/open_software/fedora/releases/8/Everything/i386/os',
  },
  # redhat 5
  'redhat-5-base': {
    'name': 'redhat-5-base',
    'baseurl': 'http://www.abodiosoftware.com/open_software/redhat/5/os/Server/',
  },
  # centos 5
  'centos-5-base': {
    'name': 'centos-5-base',
    'baseurl': 'http://www.abodiosoftware.com/open_software/centos/5/os/i386/'
  },
}
