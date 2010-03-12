from systembuilder.locals import LocalsDict, REMOVE

__all__ = ['L_INSTALLCLASS']

L_INSTALLCLASS = LocalsDict({
  "anaconda-0": # 11.1.0.7-1
'''
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %(groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    anaconda.backend.selectGroup('core', True, False)

  def setSteps(self, dispatch):
    BaseInstallClass.setSteps(self, dispatch);
    dispatch.skipStep("partition")
    dispatch.skipStep("tasksel")

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''
,
  "anaconda-11.1.2.36-1":
'''
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %(groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    anaconda.backend.selectGroup('core', True, False)

  def setSteps(self, dispatch):
    BaseInstallClass.setSteps(self, dispatch);
    dispatch.skipStep("partition")
    dispatch.skipStep("tasksel")

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''
,
  "anaconda-11.2.0.66-1":
'''
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %(groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    anaconda.backend.selectGroup('core', True, False)

  def setSteps(self, anaconda):
    BaseInstallClass.setSteps(self, anaconda);
    anaconda.dispatch.skipStep("partition")
    anaconda.dispatch.skipStep("tasksel")

  def getBackend(self, methodstr):
    if methodstr.startswith("livecd://"):
      import livecd
      return livecd.LiveCDCopyBackend
    import yuminstall
    return yuminstall.YumBackend

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''
,
  "anaconda-11.4.1.10-1":
'''
from installclass import BaseInstallClass
from constants import *
from filer import *
from flags import flags
import os, types
import iutil

import gettext
_ = lambda x: gettext.ldgettext("anaconda", x)

import installmethod
import yuminstall

import rpmUtils.arch

class InstallClass(BaseInstallClass):
  id = "custom"
  _name = N_("_Custom")
  pixmap = "custom.png"
  _description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %(groups)s)]

  bugFiler = BugzillaFiler(bugUrl="https://bugzilla.redhat.com/xmlrpc.cgi")

  def getPackagePaths(self, uri):
    if not type(uri) == types.ListType:
      uri = [uri,]

    return {'Installation Repo': uri}

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)

    if not anaconda.isKickstart:
      BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions,
                                              CLEARPART_TYPE_LINUX)

  def setSteps(self, anaconda):
    BaseInstallClass.setSteps(self, anaconda);
    anaconda.dispatch.skipStep("partition")
    anaconda.dispatch.skipStep("tasksel")

  def setGroupSelection(self, anaconda):
    anaconda.backend.selectGroup('core', True, False)

  def getBackend(self):
    if flags.livecdInstall:
      import livecd
      return livecd.LiveCDCopyBackend
    else:
      return yuminstall.YumBackend

  def __init__(self):
    BaseInstallClass.__init__(self)
''',
})
