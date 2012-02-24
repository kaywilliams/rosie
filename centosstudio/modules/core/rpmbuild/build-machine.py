#
# Copyright (c) 2011
# CentOS Solutions, Inc. All rights reserved.
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
import optparse

from centosstudio.callback     import TimerCallback
from centosstudio.cslogging    import MSG_MAXWIDTH
from centosstudio.errors       import (CentOSStudioError, 
                                       CentOSStudioEventError)
from centosstudio.event        import Event
from centosstudio.main         import Build
from centosstudio.validate     import InvalidConfigError

from centosstudio.modules.shared import PickleMixin
from centosstudio.modules.shared import SystemVirtConfigError 


def get_module_info(ptr, *args, **kwargs):
 return dict(
    api         = 5.0,
    events      = ['BuildMachineEvent',],
    description = 'creates a virtual machine for building RPMs',
  )


class BuildMachineEvent(PickleMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build-machine',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = '1.01',
      requires = ['base-treeinfo', ],
      provides = ['build-machine'],
      conditional = True,
    )

    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'variables': [], 
      'config':    [],
      'input':     [],
    }

    PickleMixin.__init__(self)

  def validate(self):
    try:
      import libvirt
    except ImportError:
      raise SystemVirtConfigError(file=self._config.file)

    if not self.config.get('definition/text()', ''):
      raise InvalidConfigError(self._config.file,
      "\n[%s]: a 'definition' element is required for building rpms" 
      % self.id)

  def setup(self):
    self.diff.setup(self.DATA)

    self.definition = self.config.get('definition/text()', '')
    self.io.validate_input_file(self.definition)
    self.DATA['input'].append(self.definition)

  def run(self):
    # start timer
    msg = "creating/updating build machine"
    if self.logger:
      timer = TimerCallback(self.logger)
      timer.start(msg)
    else:
      timer = None

    # initialize builder
    try:
      builder = Build(self._get_options(), [self.definition])
    except CentOSStudioError, e:
      raise BuildMachineCreationError(definition=self.definition, 
                                      error=e,
                                      idstr='',
                                      sep = MSG_MAXWIDTH * '=',)

    # build machine
    try:
      builder.main()
    except CentOSStudioError, e:
      raise BuildMachineCreationError(definition=self.definition, 
                                      error=e,
                                      idstr="--> build machine id: %s\n" %
                                            builder.solutionid,
                                      sep = MSG_MAXWIDTH * '=')

    # stop timer
    if timer: timer.end()

    # cache hostname
    self.pickle({'hostname': builder.cvars['publish-setup-options']
                                          ['hostname']})

  def apply(self):
    self.cvars['build-machine'] = self.unpickle().get('hostname', None)

  def _get_options(self):
    parser = optparse.OptionParser()
    parser.set_defaults(**dict(
      logthresh = 0,
      logfile   = self.options.logfile,
      libpath   = self.options.libpath,
      sharepath = self.options.sharepath,
      force_modules = [],
      skip_modules  = [],
      force_events  = ['deploy'],
      skip_events   = [],
      mainconfigpath = self.options.mainconfigpath,
      enabled_modules  = [],
      disabled_modules = [],
      list_modules = False,
      list_events = False,
      no_validate = False,
      validate_only = False,
      clear_cache = False,
      debug = self.options.debug,))

    opts, _ = parser.parse_args([])
    
    return opts


# -------- Error Classes --------#
class BuildMachineCreationError(CentOSStudioEventError):
  message = "Error creating or updating RPM build machine.\n%(sep)s\n%(idstr)s--> build machine definition: %(definition)s\n--> error:%(error)s\n"
