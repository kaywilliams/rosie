from spin.locals import LocalsDict, REMOVE

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

  tasks = [("Default", %(default_groups)s), ("Everything", %(all_groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups()
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def setSteps(self, dispatch):
    BaseInstallClass.setSteps(self, dispatch);
    dispatch.skipStep("partition")

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

  tasks = [("Default", %(default_groups)s), ("Everything", %(all_groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups(anaconda)
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def setSteps(self, dispatch):
    BaseInstallClass.setSteps(self, dispatch);
    dispatch.skipStep("partition")

  def __init__(self, expert):
    BaseInstallClass.__init__(self, expert)
'''
,
  "anaconda-11.2.0.66-1":
'''
from installclass import BaseInstallClass
from rhpl.translate import N_
from constants import *

import logging
log = logging.getLogger("anaconda")

class InstallClass(BaseInstallClass):
  id = "custom"
  name = N_("_Custom")
  pixmap = "custom.png"
  description = N_("Select the software you would like to install on your system.")
  sortPriority = 10000
  showLoginChoice = 1
  showMinimal = 1

  tasks = [("Default", %(default_groups)s), ("Everything", %(all_groups)s)]

  def setInstallData(self, anaconda):
    BaseInstallClass.setInstallData(self, anaconda)
    BaseInstallClass.setDefaultPartitioning(self, anaconda.id.partitions, CLEARPART_TYPE_LINUX)

  def setGroupSelection(self, anaconda):
    grps = anaconda.backend.getDefaultGroups(anaconda)
    log.info(grps)
    map(lambda x: anaconda.backend.selectGroup(x), grps)

  def setSteps(self, anaconda):
    BaseInstallClass.setSteps(self, anaconda);
    anaconda.dispatch.skipStep("partition")

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
})
