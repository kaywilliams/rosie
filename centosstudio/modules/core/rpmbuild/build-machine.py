#
# Copyright (c) 2012
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

import copy
import optparse
import libvirt

from centosstudio.callback       import TimerCallback
from centosstudio.cslogging      import L1, MSG_MAXWIDTH
from centosstudio.errors         import (CentOSStudioError,
                                         CentOSStudioEventError)
from centosstudio.main           import Build

from centosstudio.event          import Event
from centosstudio.modules.shared import PickleMixin

MODULE_INFO = dict(
  api         = 5.0,
  events      = ['BuildMachineEvent'],
  description = 'creates an RPM build virtual machine',
  group       = 'rpmbuild',
)

class BuildMachineEvent(PickleMixin):
  def __init__(self, ptr, *args, **kwargs):
    Event.__init__(self,
      id = 'build-machine',
      parentid = 'rpmbuild',
      ptr = ptr,
      version = '1.00',
      requires = ['base-treeinfo', 'build-machine-data'],
      provides = ['build-machine-data'],
    )

    if not self.type == 'component':
      self.enabled = False

    self.options = ptr.options # options not exposed as shared event attr

    self.DATA = {
      'variables': [], 
      'config':    [],
      'input':     [],
    }

    PickleMixin.__init__(self)

  def setup(self):
    self.diff.setup(self.DATA)

    self.definition = self.cvars['build-machine-data']['definition']
    self.io.validate_input_file(self.definition)
    self.DATA['input'].append(self.definition)

  def run(self):
    builder = CentOSStudioInterface(self, self.definition)

    # start timer
    msg = "creating/updating virtual machine"
    if self.logger:
      timer = TimerCallback(self.logger)
      timer.start(msg)
    else:
      timer = None

    # build machine
    try:
      info = builder.build()
    except (KeyboardInterrupt, SystemExit):
      raise
    except CentOSStudioError, e:
      # provide solutionid in error msg, if available
      raise BuildMachineCreationError(definition=self.definition, 
                                      error=e,
                                      sep = MSG_MAXWIDTH * '=',)

    # stop timer
    if timer: timer.end()

    # cache hostname
    self.pickle({'hostname': info.cvars['publish-setup-options']['hostname']})

  def apply(self):
    self.cvars['build-machine-data']['hostname'] = self.unpickle(
                                                   ).get('hostname', None)


class CentOSStudioInterface(object):
    def __init__(self, ptr, definition):
        self.definition = definition
        self.ptr = ptr

    def build(self):
        parser = optparse.OptionParser()
        parser.set_defaults(**dict(
          logthresh = 0,
          logfile   = self.ptr.options.logfile,
          libpath   = self.ptr.options.libpath,
          sharepath = self.ptr.options.sharepath,
          force_modules = [],
          skip_modules  = [],
          force_events  = [],
          skip_events   = [],
          mainconfigpath = self.ptr.options.mainconfigpath,
          enabled_modules  = [],
          disabled_modules = [],
          list_modules = False,
          list_events = False,
          no_validate = False,
          validate_only = False,
          clear_cache = False,
          debug = self.ptr.options.debug,))

        opts, _ = parser.parse_args([])
     
        # initialize our builder with opts and make it go!
        rpmbuilder = Build(opts, [self.definition])
        rpmbuilder.main()

        return rpmbuilder


class BuildMachineCreationError(CentOSStudioEventError):
  message = "Error creating or updating RPM build machine.\n%(sep)s\n--> build machine definition: %(definition)s'\n--> error:%(error)s\n"
