#
# Copyright (c) 2007, 2008
# Rendition Software, Inc. All rights reserved.
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
"config.py - make a config 'file' for spin tests"

import copy

from StringIO import StringIO

from rendition.xmllib import config

def make_repos(distro, repodefs=[]):
  "make a <repos> top level element with the base repo included"
  repos = config.Element('repos')
  repos.append(config.Element('base-repo', text='%s-base' % distro))
  for repo in repodefs:
    if repo is None: continue
    repos.append(repo)
  return repos

def make_main(eventid, arch, **kwargs):
  "make a <main> top level element"
  main = config.Element('main')

  kwargs.setdefault('fullname', '%s event test' % eventid)
  kwargs.setdefault('product',  'test-%s' % eventid)
  kwargs.setdefault('version',  '0')
  kwargs.setdefault('arch', arch)

  for k,v in kwargs.items():
    config.Element(k, text=v, parent=main)
  return main

def make_default_config(eventid, basedistro='fedora-6', arch='i386'):
  "create a default config file"
  # make top level element
  distro = _make_distro()
  # make main element and append
  distro.append(make_main(eventid, arch))
  # make repos element
  baserepo = _make_repo('%s-base' % basedistro, arch)
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

def _make_repo(id, arch='i386', **kwargs):
  "construct a repo, either from data in REPOS, below, or from kwargs"
  if id in REPOS.keys():
    d = copy.copy(REPOS[id])
  else:
    return #! d = {}

  d.update(kwargs)

  for k in ['baseurl']: # make sure repo has all necessary/expected fields
    if not d.has_key(k):
      raise ValueError("Missing key '%s' for repo '%s'" % (k, id))

  repo = config.Element('repo', attrs={'id': id})
  for k,v in d.items():
    config.Element(k, text=v % {'arch': arch}, parent=repo)

  return repo

REPOS = {
  # fedora 6
  'fedora-6-base': {
    'name': 'fedora-6-base',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/core/6/%(arch)s/os/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/core/6/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  'fedora-6-updates': {
    'name': 'fedora-6-updates',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/core/updates/6/%(arch)s/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/core/6/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  # fedora 7
  'fedora-7-base': {
    'name': 'fedora-7-base',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Fedora/%(arch)s/os/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Fedora/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  'fedora-7-updates': {
    'name': 'fedora-7-updates',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/updates/7/%(arch)s/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Fedora/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  'fedora-7-everything': {
    'name': 'fedora-7-everything',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Everything/%(arch)s/os/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/releases/7/Fedora/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  # fedora 8
  'fedora-8-base': {
    'name': 'fedora-8-base',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Fedora/%(arch)s/os/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Fedora/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  'fedora-8-updates': {
    'name': 'fedora-8-updates',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/updates/8/%(arch)s/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Fedora/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  'fedora-8-everything': {
    'name': 'fedora-8-everything',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Everything/%(arch)s/os',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/releases/8/Fedora/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  # fedora devel
  'fedora-devel-base': {
    'name': 'fedora-devel-base',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/fedora/development/%(arch)s/os/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/fedora/development/%(arch)s/os/RPM-GPG-KEY-fedora',
  },
  # redhat 5
  'redhat-5-base': {
    'name': 'redhat-5-base',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/redhat/linux/enterprise/5Server/en/os/%(arch)s/Server/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/redhat/linux/enterprise/5Server/en/os/%(arch)s/RPM-GPG-KEY-redhat-release',
  },
  # centos 5
  'centos-5-base': {
    'name': 'centos-5-base',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/centos/5/os/%(arch)s/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/centos/5/os/%(arch)s/RPM-GPG-KEY-CentOS-5',
  },
  'centos-5-updates': {
    'name': 'centos-5-updates',
    'baseurl': 'http://www.renditionsoftware.com/mirrors/centos/5/updates/%(arch)s/',
    'gpgkey':  'http://www.renditionsoftware.com/mirrors/centos/5/os/%(arch)s/RPM-GPG-KEY-CentOS-5',
  }
}
