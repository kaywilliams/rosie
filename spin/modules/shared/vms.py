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
import rpm
import sha
import yum

from rendition import pps

from rendition.repo import RPM_PNVRA_REGEX

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

  def read_kickstart(self):
    # add various metadata stuff
    self.DATA['input'].append(self.cvars['kickstart-file'])
    self.DATA['variables'].append('cvars[\'kickstart-file\']')

    return imgcreate.read_kickstart(self.cvars['kickstart-file'])

  def _update_ks_repos(self, ks):
    # replace repos in kickstart with repo pointing to published appliance
    ks.handler.repo.repoList = []
    ks.handler.repo.parse(['--name',    'appliance',
                           '--baseurl', 'file://%s'
                             % self.cvars['repodata-directory'].dirname])

    self.DATA['variables'].append('cvars[\'repodata-directory\']')


  def _prep_ks_scripts(self, ks):
    # prepare a variable we can easily compare in difftest. This variable
    # ignores script properties we don't care about (lineno, logfile).
    self._scripts = []
    self.DATA['variables'].append('_scripts')

    for s in ks.handler.scripts:
      # storing script shasum for both whitespace and md size concerns
      self._scripts.append(dict(scriptsha = sha.new(s.script).hexdigest(),
                                interp    = s.interp,
                                inChroot  = s.inChroot,
                                type      = s.type))

  def _check_ks_scripts(self):
    # since we can't guarantee that scripts are idempotent (they're supplied
    # by users), we have to regenerate the chroot any time they change
    # annoying and inefficient, but also the only way we can be sure to get
    # all changes
    if ( not self.forced and
         ( len(self.diff.variables.difference()) == 1 and
           self.diff.variables.difference('_scripts') ) ):
      # if we're not forced and the only difference between this run and last
      # run is in the _scripts variable...
      self.log(3, L1("one or more scripts changed in kickstart; "
                     "regenerating raw image"))
      self.vmdir.rm(recursive=True, force=True) # remove any previous base

class SpinImageCreatorMixin:
  def __init__(self, event, *args, **kwargs):

    self.event = event

    # create temporary files within the mddir instead of in /var/tmp
    self.tmpdir = event.tmpdir
    self.tmpdir.mkdirs()

    self._base = None # older image to use, if available

  # yay thanks for making it easy to subclass!
  # this is an Xtreme Kool Hak that makes my life (slightly) easier when
  # trying to access all the dumb double-underscore attributes imgcreate
  # likes to use
  def _getattr_(self, attr):
    for cls in inspect.getmro(self.__class__):
      if cls == SpinImageCreatorMixin: continue # don't look in this class
      try:
        return getattr(self, '_%s%s' % (cls.__name__, attr))
      except:
        pass
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

  def __select_packages(self, ayum):
    # select new packages in pkglist if we're using an existing chroot
    if not self._base:
      self._getattr_('__select_packages')(ayum)
    else:
      diff = self.event.diff.variables.difference("cvars['pkglist']")

      if diff is not None:
        prev = [ RPM_PNVRA_REGEX.match(x+'.rpm').group('name')
                 for x in diff[0] ]
        next = [ RPM_PNVRA_REGEX.match(x+'.rpm').group('name')
                 for x in diff[1] ]

        for pkg in set(next) - set(prev):
          ayum.install(name = pkg)

  def __select_groups(self, ayum):
    # don't select groups at all if we're using an existing chroot
    if not self._base:
      self._getattr_('__select_groups')(ayum)
    else:
      pass

  def __deselect_packages(self, ayum):
    # remove old packages in pkglist if we're using an exising chroot
    if not self._base:
      self._getattr_('__deselect_packages')(ayum)
    else:
      diff = self.event.diff.variables.difference("cvars['pkglist']")

      if diff is not None:
        prev = [ RPM_PNVRA_REGEX.match(x+'.rpm').group('name')
                 for x in diff[0] ]
        next = [ RPM_PNVRA_REGEX.match(x+'.rpm').group('name')
                 for x in diff[1] ]

        for pkg in (set(prev) - set(next)):
          ayum.remove(name = pkg)

  def __update_packages(self, ayum):
    if not self._base:
      return
    else:
      diff = self.event.diff.variables.difference("cvars['pkglist']")

      if diff is not None:
        # obtain list of newly-added and removed package names
        new = [ RPM_PNVRA_REGEX.match(x+'.rpm').group('name')
                for x in set(diff[1]) - set(diff[0]) ]
        old = [ RPM_PNVRA_REGEX.match(x+'.rpm').group('name')
                for x in set(diff[0]) - set(diff[1]) ]

        # if a package was in both lists, this means it needs to be updated
        for pkg in set(new) & set(old):
          ayum.update(name = pkg)

  def __can_handle_selinux(self, ayum):
    # rewritten to handle incremental check
    file = '/usr/sbin/lokkit'
    if ( not imgcreate.kickstart.selinux_enabled(self.ks) and
         pps.path('/selinux/enforce').exists() and
         not ayum.installHasFile(file) and
         not (pps.path(self._instroot)//file).exists() ): # check instroot too
      raise CreatorError("Unable to disable SELinux because the installed "
                         "package set did not inclue the file '%s'" % file)

  def install(self, repo_urls = None):
    yum_conf = pps.path(self._mktemp(prefix = "yum.conf-"))

    ayum = imgcreate.yuminst.LiveCDYum()
    ayum.setup(yum_conf, self._instroot)
    ayum.conf.obsoletes = 1 # enable obsoletes processing

    for repo in imgcreate.kickstart.get_repos(self.ks, repo_urls or {}):
      (name, baseurl, mirrorlist, inc, exc) = repo

      yr = ayum.addRepository(name, baseurl, mirrorlist)
      if inc:
        yr.includepkgs = inc
      if exc:
        yr.exclude = exc

    if imgcreate.kickstart.exclude_docs(self.ks):
      rpm.addMacro("_excludedocs", "1")
    if not imgcreate.kickstart.selinux_enabled(self.ks):
      rpm.addMacro("__file_context_path", "%{nil}")

    try:
      self.__select_packages(ayum)
      self.__update_packages(ayum)
      self.__select_groups(ayum)
      self.__deselect_packages(ayum)

      self.__can_handle_selinux(ayum)

      ayum.runInstall()
    except imgcreate.CreatorError, e:
      # imgcreate raises an exception in the case when the transaction set
      # is empty.  In this case, we don't care; that just means yum doesn't
      # have any work do to.  If we get a CreatorError and the tsInfo isn't
      # empty, though, then we have a problem
      if len(ayum.tsInfo) != 0: raise
    except yum.Errors.RepoError, e:
      raise imgcreate.CreatorError("Unable to download from repo : %s" % e)
    except yum.Errors.YumBaseError, e:
      raise imgcreate.CreatorError("Unable to install : %s" % e)
    finally:
      ayum.closeRpmDB()
      ayum.close()
      yum_conf.remove()

    # do some clean up to avoid lvm leakage.  this sucks.
    for subdir in ("cache", "backup", "archive"):
      lvmdir = pps.path(self._instroot)/'etc/lvm'/subdir
      if lvmdir.exists():
        for f in lvmdir.listdir():
          f.rm(force=True)
