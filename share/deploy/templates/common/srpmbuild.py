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
                 *args, **kwargs):
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

    def check_status(self):
        "uses current and last srpm name, version and release to determine"
        "whether a new srpm should be built"
        raise NotImplementedError()

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

    def __init__(self, id, input, last, patches=None,
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

    def check_status(self):
      "compares current nvr to last _nvr; returns false if they differ"
      if self.last:
        # get last nvr
        dist = shlib.execute('rpm --eval "%{dist}"')[0]
        name, ver, rel, _, _ = miscutils.splitFilename(self.last)
        last_nvr = [name, ver, rel.replace(dist, '')]

        # get curr nvr
        curr = self.nvra
        curr_nvr = [ curr['name'], curr['version'], curr['release'] ]

        # compare
        if last_nvr == curr_nvr: return False
        
      return True

    def build_srpm(self):
        for dir in ('BUILD', 'SRPMS', 'SPECS', 'SOURCES', 'RPMS'):
            (self.builddir / dir).mkdirs()
        self.make_srpm()
        name = self.nvra['name']
        ver  = self.nvra['version']
        srpm = (self.builddir / 'SRPMS').findpaths(
            glob='%s-%s-*.src.rpm' % (name, ver), maxdepth=1)[0]
        #self.apply_patches()
        return srpm

    def make_srpm(self):
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

    def _get_local_sources(self):
        raise NotImplementedError()


class FolderFetcher(LocalFetcher):
    type = 'folder'
    def __init__(self, id, input, last, patches=None,
                 username=None, password=None,
                 *args, **kwargs):
        LocalFetcher.__init__(self, id, input, last, patches=patches,
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
    def __init__(self, id, input, last, patches=None,
                 username=None, password=None,
                 *args, **kwargs):
        LocalFetcher.__init__(self, id, input, last, patches=patches,
                              username=username, password=password, *args, 
                              **kwargs)


class MercurialFetcher(ScmFetcher):
    type = 'mercurial'
    arguments = ['makefile', 'revision']

    def __init__(self, id, input, last, patches=None, username=None, 
                 password=None, revision=None,
                 *args, **kwargs):
        ScmFetcher.__init__(self, id, input, last, patches=patches,
                            username=username, password=password,
                            *args, **kwargs)

        self.revision = revision or 'tip'


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
        shlib.execute('hg clone --quiet --rev %s %s' % (self.revision, 
                                                        self.input))
      else:
        shlib.execute('hg clone --rev %s %s' % (self.revision, self.input))
      os.chdir(cwd)
      self._local_sources = local_sources
      return self._local_sources

CLASS_MAP = { 'folder': FolderFetcher,
              'mercurial': MercurialFetcher }

def main(id, input, output, last, username, password, type, *args, **kwargs):
  cls = CLASS_MAP[type]

  fetcher = cls(id, input=input, last=last, 
                             username=username, password=password, 
                             revision=None, *args, **kwargs)
  fetcher.set_defaults(quiet_mode=False)
  if fetcher.check_status():
    try:
      clean_output(output)
      srpm = fetcher.build_srpm()
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
  input = pps.path(sys.argv[2]) # e.g. url to mercurial repository
  output = pps.path(sys.argv[3]) # location to copy final srpm
  last = sys.argv[4] # filename of last srpm
  type = sys.argv[5] # 'folder' or 'mercurial'

  # TODO - add input validation and useful errors

  if last == "None" : last = None

  main(id=srpmid, input=input, output=output, last=last, type=type, 
       username=None, password=None)
