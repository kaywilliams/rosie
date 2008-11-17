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

import imgcreate
import inspect
import os
import rpm
import sha
import subprocess
import sys
import yum

from yum import _

from rendition import pps
from rendition import rxml

from rendition.repo import RPM_PNVRA_REGEX

from spin.errors  import SpinError
from spin.logging import L1, L2

class VmCreateMixin:

  def error(self, e):
    # clean up creator on error, don't move other output
    self.creator and self.creator.cleanup()
    if self.mdfile.exists():
      debugdir = self.mddir+'.debug'
      debugdir.mkdir()
      self.mdfile.rename(debugdir/self.mdfile.basename)
    ##Event.error(self, e) # don't do this, this deletes output

  def _prep_ks_scripts(self):
    # prepare a variable we can easily compare in difftest. This variable
    # ignores script properties we don't care about (lineno, logfile).
    self._scripts = []
    self.DATA['variables'].append('_scripts')

    for s in self.ks.handler.scripts:
      # storing script shasum for both whitespace and md size concerns
      self._scripts.append(dict(scriptsha = sha.new(s.script).hexdigest(),
                                interp    = s.interp,
                                inChroot  = s.inChroot,
                                type      = s.type))

  def _prep_partitions(self):
    # do the same as _prep_ks_scripts, but for partitions instead
    self._partitions = []
    self.DATA['variables'].append('_partitions')

    for p in self.ks.handler.partition.partitions:
      self._partitions.append(dict(size       = s.size,
                                   disk       = s.disk,
                                   mountpoint = s.mountpoint,
                                   fstype     = s.fstype))

  def _check_ks_scripts(self):
    # since we can't guarantee that scripts are idempotent (they're supplied
    # by users), we have to regenerate the chroot any time they change
    # annoying and inefficient, but also the only way we can be sure to get
    # all changes
    if ( not self.forced and
         self.mdfile.exists() and
         self.diff.variables.difference('_scripts') ):
      # if we're not forced and the only difference between this run and last
      # run is in the _scripts variable...
      self.log(3, L1("kickstart scripts have changed; regenerating image"))
      return False
    return True

  def _check_partitions(self):
    # if partitions change in any meaningful way, start over
    if ( not self.forced and
         self.mdfile.exists() and
         self.diff.variables.difference('_scripts') ):
      self.log(3, L1("partition layout has changed; regenerating image"))
      return False
    return True


class SpinImageCreatorMixin:
  def __init__(self, event, *args, **kwargs):

    self.event = event

    # create temporary files within the mddir instead of in /var/tmp
    self.tmpdir = event.tmpdir
    self.tmpdir.mkdirs()

    self._base = None # older image to use, if available

  # yay thanks for making it easy to subclass!
  # this is an Xtreem Kool Hak that makes my life (slightly) easier when
  # trying to access all the dumb double-underscore attributes imgcreate
  # likes to use
  def _getattr_(self, attr):
    for cls in inspect.getmro(self.__class__):
      if cls == SpinImageCreatorMixin: continue # don't look in this class
      atn = '_%s%s' % (cls.__name__, attr)
      if hasattr(self, atn):
        return getattr(self, atn)
    else:
      raise AttributeError(attr)

  def _setattr_(self, attr, v):
    # this is slightly different behavior than standard setattr; it doesn't
    # setattr on the outermost instance class, and it errors if no parent
    # class instance defines the attr
    for cls in inspect.getmro(self.__class__):
      if cls == SpinImageCreatorMixin: continue # don't look in this class
      atn = '_%s%s' % (cls.__name__, attr)
      if hasattr(self, atn):
        setattr(self, atn, v)
        return
    else:
      raise AttributeError(attr)

  def _get__builddir(self):
    return self._getattr_('__builddir')
  def _set__builddir(self, v):
    self._setattr_('__builddir', v)
  __builddir = property(_get__builddir, _set__builddir)

  def _base_on(self, base_on):
    # subclasses are responsible for calling this method if a base_on is used
    self._base = base_on

  def cleanup(self):
    # don't delete the install tree on error
    if not self.__builddir:
      return

    self.unmount()

    self._cleanup() # creator specific cleanup (usually saving output)

    pps.path(self.__builddir).rm(recursive=True, force=True)
    self.__builddir = None

  def _cleanup(self):
    pass

  def _tx_packages(self):
    # return a tuple of add, remove, update package lists
    if not self._base:
      i = set(self.event.cvars['pkglist-install-packages'])
      r = set()
      u = set()
    else:
      diff = self.event.diff.variables.difference("cvars['pkglist-install-packages']")
      i = set()
      r = set()
      u = set()

      if diff is not None:
        prev = set([ x for x in diff[0] ])
        next = set([ x for x in diff[1] ])
        i = next - prev # stuff in next not in prev
        r = prev - next # stuff in prev not in next
        u = next & prev # stuff in both next and prev

    return i,r,u

  def _check_required_packages(self):
    # raise an exception if appliance doesn't include all required packages
    pass

  def _get_pkglist_names(self):
    return self.event.cvars['pkglist-install-packages']

  def install(self, repo_urls = None):
    yum_conf = pps.path(self._mktemp(prefix = "yum.conf-"))

    cmd = ['python', pps.path(__file__),
                     '--installroot', self._instroot,
                     '--conf', yum_conf]
    for name,baseurl,_,_,_ in imgcreate.kickstart.get_repos(self.ks, repo_urls or {}):
      cmd.extend(['--repo', '%s:%s' % (name, baseurl)])
    if imgcreate.kickstart.exclude_docs(self.ks):
      cmd.append('--excludedocs')
    if imgcreate.kickstart.selinux_enabled(self.ks):
      cmd.append('--selinux')

    # construct yum shell-like command list for install
    add, remove, update = self._tx_packages()
    stdin = []
    for pkg in add:    stdin.append('install %s' % pkg)
    for pkg in remove: stdin.append('remove %s'  % pkg)
    for pkg in update: stdin.append('update %s'  % pkg)

    try:
      self._check_required_packages() # make sure we have the packages we need
      p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
      try:
        stdout,stderr = p.communicate('\n'.join(stdin))
        if p.returncode != 0:
          raise imgcreate.CreatorError("Unable to install: %s" % stderr)
      except BaseException, e: # except all exceptions
        # make sure RPM has finished doing stuff before we raise our exception
        # to try and clean stuff up - ignore keyboard interrupts until it
        # finishes
        while True:
          try:
            p.wait()
            raise e
          except:
            if p.returncode is not None: # finished
              raise
    finally:
      yum_conf.remove()

    # do some clean up to avoid lvm leakage.  this sucks.
    for subdir in ("cache", "backup", "archive"):
      lvmdir = pps.path(self._instroot)/'etc/lvm'/subdir
      if lvmdir.exists():
        for f in lvmdir.listdir():
          f.rm(force=True)

class VMYum(imgcreate.yuminst.LiveCDYum):
  def __init__(self):
    imgcreate.yuminst.LiveCDYum.__init__(self)

  def resolveDeps(self):
    # we don't need to do any depsolving because all the packages in
    # the transaction set are resolved.
    if len(self.tsInfo) == 0:
      return (0, ['Success - empty transaction'])
    else:
      return (2, ['Success - deps resolved'])

  def runInstall(self):
    os.environ["HOME"] = "/"

    try:
      (res, resmsg) = self.buildTransaction()
    except yum.Errors.RepoError, e:
      raise imgcreate.CreatorError("Unable to download from repo : %s" %(e,))
    if res != 2:
      raise imgcreate.CreatorError("Failed to build transaction : %s" % str.join("\n", resmsg))

    dlpkgs = map(lambda x: x.po, filter(lambda txmbr: txmbr.ts_state in ("i", "u"), self.tsInfo.getMembers()))
    self.downloadPkgs(dlpkgs)
    # FIXME: sigcheck?

    self.initActionTs()
    self.populateTs(keepold=0)
    deps = self.ts.check()
    if len(deps) != 0:
      raise imgcreate.CreatorError("Dependency check failed!")
    rc = self.ts.order()
    if rc != 0:
      raise imgcreate.CreatorError("ordering packages for installation failed!")

    # FIXME: callback should be refactored a little in yum
    sys.path.append('/usr/share/yum-cli')
    import callback
    cb = callback.RPMInstallCallback()
    cb.tsInfo = self.tsInfo
    cb.filelog = False
    ret = self.runTransaction(cb)
    print ""
    return ret

class RequiresKickstartError(SpinError):
  message = ( "The '%(modid)s' module requires that a kickstart be specified "
              "in the <kickstart> top-level element." )


# The following hack solves two problems with imgcreate
#  1) canceling an install via CTRL+C during rpm installation doesn't call
#     imgcreate's cleanup methods because of RPM's interrupt signal handling
#  2) multiple runs of imgcreate within the same session seem to have some
#     sort of issue where the lockfile from the previous run sticks around
#     instead of using a new value
#
# When this script is executed directly, it instead acts as a yum installer,
# more or less.  (See below for script options.) It reads commands from
# stdin, accepting '[install|remove|update] <pkgname>'.
#
# Since this process is in a subshell, cancelling via CTRL+C merely kills
# the subshell and returns control to the parent python instance, allowing
# us to properly clean up.  Furthermore, since each execution is performed
# in a separate subshell, there is no data persistence issue around to cause
# issue 2.
#
# Problem solved, albeit in a very hacky and ugly way.

import optparse

def makeparser():
  parser = optparse.OptionParser()

  parser.add_option('--installroot')
  parser.add_option('--conf')
  parser.add_option('--repo', action='append', default=[])
  parser.add_option('--excludedocs', action='store_true', default=False)
  parser.add_option('--selinux', action='store_true', default=False)

  return parser

def _can_handle_selinux(ayum):
  file = '/usr/sbin/lokkit'
  if ( pps.path('/selinux/enforce').exists() and
       not ayum.installHasFile(file) and
       not (pps.path(ayum.conf.installroot)//file).exists() ): # check instroot too
    raise imgcreate.CreatorError(
      "Unable to disable SELinux because the installed package set did "
      "not include the file '%s'" % file)

if __name__ == '__main__':
  parser = makeparser()
  opts,args = parser.parse_args(sys.argv[1:])

  ayum = VMYum()
  ayum.setup(opts.conf, opts.installroot)
  ayum.conf.obsoletes = 1 # enable obsoletes processing

  for repo in opts.repo:
    name, baseurl = repo.split(':', 1)
    ayum.addRepository(name, baseurl, None)

  if opts.excludedocs:
    rpm.addMacro('_excludedocs', '1')
  if not opts.selinux:
    rpm.addMacro('__file_context_path', '%{nil}')

  try:
    try:
      for line in sys.stdin.readlines():
        cmd, arg = line.split()
        if   cmd == 'install': ayum.install(name = arg)
        elif cmd == 'update':  ayum.update(name = arg)
        elif cmd == 'remove':  ayum.remove(name = arg)
        else: raise ValueError(cmd)
    except yum.Errors.RepoError, e:
      raise imgcreate.CreatorError("Unable to download from repo: %s" % e)
    except yum.Errors.YumBaseError, e:
      raise imgcreate.CreatorError("Unable to install: %s" % e)

    # if selinux isn't enabled on host machine, check to see if we can diable
    # raises imgcreate.CreatorError
    if not opts.selinux:
      _can_handle_selinux(ayum)

    try:
      ayum.runInstall()
    except imgcreate.CreatorError, e:
      # imgcreate raises an exception in the case when the transaction set
      # is empty.  In this case, we don't care; that just means yum doesn't
      # have any work do to.  If we get a CreatorError and the tsInfo isn't
      # empty, though, then we have a problem
      if len(ayum.tsInfo) != 0: raise
  finally:
    ayum.closeRpmDB()
    ayum.close()
