#!/usr/bin/python
import os
import shlex
import sys
import traceback

from rpmUtils import miscutils

from deploy.util import pps
from deploy.util import shlib

SRPMBUILD_BASE = '/tmp/srpmbuild'

class Fetcher:
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            type.__init__(cls, name, bases, dict)

    def __init__(self, id, input, patches=None,
                 username=None, password=None,
                 last=None, *args, **kwargs):
        self.id = id
        self._input = pps.path(input).normpath()

        self.last = last

        self.username = username 
        self.password = password

        self.builddir = pps.path('%s-%s' % (SRPMBUILD_BASE, self.id))
        self.builddir.rm(force=True, recursive=True)
        self.builddir.mkdirs()

    @classmethod
    def set_defaults(cls, quiet_mode):
        cls.QUIET_MODE   = quiet_mode

    @property
    def input(self):
        return self._input

    #----- METHODS TO BE IMPLEMENTED BY CHILDREN OBJECTS -----#
    def initialize(self):
        pass

    def build_srpm(self):
        "returns the path to the built srpm"
        raise NotImplementedError()

    def clean(self):
        pass

    def finalize(self):
        pass


class LocalFetcher(Fetcher):
    type = 'local'
    arguments = ['makefile']

    def __init__(self, id, input, patches=None,
                 username=None, password=None,
                 makefile=None,
                 *args, **kwargs):
        Fetcher.__init__(self, id, input, patches=patches,
                         username=username, password=password,
                         *args, **kwargs)
        self.makefile = makefile or None

        self._local_sources = None
        self._nvra = None

    @property
    def sources(self):
        dir = self.builddir / 'sources'
        dir.mkdirs()
        return dir

    @property
    def local_sources(self):
        return self._get_local_sources()

    @property
    def nvra(self):
        if self._nvra is not None:
            return self._nvra
        name = shlib.execute("grep 'Name:' %s | sed -e 's/Name: //'" % self.spec_file)[0]
        arch = shlib.execute("grep 'BuildArch:' %s | sed -e 's/BuildArch: //'" % self.spec_file)[0]
        version = shlib.execute("grep 'Version:' %s | sed -e 's/Version: //'" % self.spec_file)[0]
        release = shlib.execute("grep 'Release:' %s | sed -e 's/Release: //' | sed -e 's/%%{?dist}//'" % self.spec_file)[0]
        name = name.strip()
        arch = arch.strip()
        version = version.strip()
        release = release.strip()
        self._nvra = {
            'name': name,
            'version': version,
            'release': release,
            'arch': arch,
        }
        return self._nvra

    @property
    def spec_file(self):
        try:
            file = self.local_sources.findpaths(glob='%s.spec' % self.id)[0]
        except IndexError, e:
            try:
                file = self.local_sources.findpaths(glob='*.spec')[0]
            except IndexError, e:
                raise RuntimeError("No spec file '%s.spec' found" % self.id)
        return file

    def build_srpm(self):
        srpm = self.make_srpm()

        # if the name of the current srpm is the same as the last srpm,
        # but the content differs, bump the spec release and rebuild
        if (self.last and
            self.last.basename == srpm.basename and      
            shlib.execute('/usr/bin/rpmdev-diff -q %s %s'
                         % (self.last_archive(), self.curr_archive(srpm)))):
          self.bump_spec()
          self._nvra = None # force spec to be reread
          srpm = self.make_srpm()
        return srpm

    def make_srpm(self):
        for dir in ('BUILD', 'SRPMS', 'SPECS', 'SOURCES', 'RPMS'):
            (self.builddir / dir).rm(recursive=True, force=True)
            (self.builddir / dir).mkdirs()

        cwd = os.getcwd()
        os.chdir(str(self.local_sources))
        if self.makefile is not None:
            preface = "make srpm --makefile %s" % self.makefile
        else:
            preface = "make srpm"
        args = ("%s --quiet BUILDARGS='--define=\"_topdir %s\" --nodeps' " 
                % (preface, str(self.builddir)))
        shlib.execute(args, verbose=self.QUIET_MODE)
        os.chdir(cwd)

        name = self.nvra['name']
        ver  = self.nvra['version']
        srpm = (self.builddir / 'SRPMS').findpaths(
            glob='%s-%s-*.src.rpm' % (name, ver), maxdepth=1)[0]

        return srpm

    def bump_spec(self):
      shlib.execute("/usr/bin/rpmdev-bumpspec -u 'Deploy Automated Package Builder' '%s'" % self.spec_file)

    def curr_archive(self, curr):
        dir = self.builddir / 'archives' / 'curr'
        dir.mkdirs()
        return  dir / shlib.execute(
                      '/usr/bin/rpmdev-extract -C %s %s | grep -v "\.spec"'
                      % (dir, curr))[0]

    def last_archive(self):
        dir = self.builddir / 'archives' / 'last'
        dir.mkdirs()
        return dir / shlib.execute(
                     '/usr/bin/rpmdev-extract -C %s %s | grep -v "\.spec"'
                     % (dir, self.last))[0]

    def _get_local_sources(self):
        raise NotImplementedError()


class FolderFetcher(LocalFetcher):
    type = 'folder'
    def __init__(self, id, input, patches=None,
                 username=None, password=None,
                 *args, **kwargs):
        LocalFetcher.__init__(self, id, input, patches=patches,
                              username=username, password=password,
                              *args, **kwargs)

    def _get_local_sources(self):
        if self._local_sources is not None:
            return self._local_sources
        if not isinstance(self.input, pps.Path.local._LocalPath):
            # 'folder' types cannot handle non-local paths.
            raise RuntimeError("A FolderFetcher object cannot handle '%s' "
                               "objects" % self.input.__class__.__name__)
        self._local_sources = self.input 
        return self._local_sources

class ScmFetcher(LocalFetcher):
    type = 'scm'
    def __init__(self, id, input, patches=None,
                 username=None, password=None,
                 *args, **kwargs):
        LocalFetcher.__init__(self, id, input, patches=patches,
                              username=username, password=password, *args, 
                              **kwargs)


class GitFetcher(ScmFetcher):
    type = 'git'
    arguments = ['makefile', 'branch']

    def __init__(self, id, input, patches=None, username=None, 
                 password=None, branch=None,
                 *args, **kwargs):
        ScmFetcher.__init__(self, id, input, patches=patches,
                            username=username, password=password,
                            *args, **kwargs)

        self.branch = branch or 'HEAD'


    @property
    def input(self):
        return self._input

    def _get_local_sources(self):
      if self._local_sources is not None:
        return self._local_sources
      cwd = os.getcwd()
      local_sources = self.builddir / self.input.basename
      os.chdir(self.builddir)
      if local_sources.exists():
        local_sources.rm(recursive=True, force=True)
      if self.QUIET_MODE:
        shlib.execute('git clone -q --branch %s %s' % (self.branch, 
                                                        self.input))
      else:
        shlib.execute('git clone --branch %s %s' % (self.branch, self.input))
      os.chdir(cwd)
      self._local_sources = local_sources
      return self._local_sources

CLASS_MAP = { 'folder': FolderFetcher,
              'git': GitFetcher }

def main(id, input, output, last, username, password, type,
         *args, **kwargs):
  cls = CLASS_MAP[type]

  fetcher = cls(id, input=input, last=last,  username=username,
                    password=password, branch=None, *args, **kwargs)
  fetcher.set_defaults(quiet_mode=False)

  try:
    srpm = fetcher.build_srpm()
    if not last or not srpm.basename == last.basename:
      clean_output(output)
      srpm.cp(output)
  except Exception:
    message = ("An error occurred building the '%s' srpm:\n'%s'\n"
               "A copy of the srpm build environment is at '%s'. "
               "This folder will be removed automatically at "
               "the start of the next '%s' build."
               % (id, traceback.format_exc(), fetcher.builddir, id))
    raise RuntimeError(message)

  fetcher.builddir.rm(force=True, recursive=True)    
  sys.exit()

def clean_output(output):
  old_srpms = output.findpaths(mindepth=1, type=pps.constants.TYPE_FILE)
  for path in old_srpms: 
    path.rm(force=True)

if __name__ == '__main__':
  srpmid = sys.argv[1]
  input = pps.path(sys.argv[2]) # e.g. url to source content 
  output = pps.path(sys.argv[3]) # location to copy final srpm
  last = pps.path(sys.argv[4]) # path to last srpm
  type = sys.argv[5] # 'folder' or 'git'

  # TODO - add input validation and useful errors

  if last == "None" : last = None

  main(id=srpmid, input=input, output=output, last=last, type=type, 
       username=None, password=None)
