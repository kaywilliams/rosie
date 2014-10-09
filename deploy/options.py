
# Copyright (c) 2014
# Deploy Foundation. All rights reserved.
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
"""
options.py

OptionParser class for use with Deploy
"""
from optparse import OptionParser, OptionGroup, SUPPRESS_HELP
from deploy.util.CleanHelpFormatter import CleanHelpFormatter


class DeployOptionParser(OptionParser):
  def __init__(self):
    OptionParser.__init__(self, "usage: %prog [OPTIONS] DEFINITION",
                          formatter=CleanHelpFormatter(),
                          description="runs deploy program to complete actions "
                                      "specified in DEFINITION"
                          )

    self.add_option('--macro', metavar='ID:VALUE',
      dest='macros',
      default=[],
      action='append',
      help='id:value pair (--macro "id:value") for replacing macros in '
           'DEFINITION')
    self.add_option('--offline',
      dest='offline',
      action='store_true',
      default=False,
      help=('do not attempt to download remote files; access from cache '
            'if available'))

    self.add_option('--debug',
      dest='debug',
      action='store_true',
      default=None,
      help=SUPPRESS_HELP)
    self.add_option('--no-debug',
      dest='debug',
      action='store_false',
      help=SUPPRESS_HELP)

    config_group = OptionGroup(self, "config options")
    config_group.add_option('-c', '--config', metavar='PATH',
      default='/etc/deploy/deploy.conf',
      dest='mainconfigpath',
      help="specify path to the deploy config file")
    config_group.add_option('--no-validate',
      dest='no_validate',
      action='store_true',
      default=False,
      help="do not validate config/definition files")
    config_group.add_option('--validate-only',
      dest='validate_only',
      default=False,
      action='store_true',
      help="validate config/definition files and exit")
    config_group.add_option('--data-root', metavar='PATH',
      dest='data_root',
      default=None,
      help="specify root directory to create definition data folders")
    config_group.add_option('--list-data-dir',
      action='store_true',
      default=False,
      dest='list_data_dir',
      help='list definition data folder and exit')
    self.add_option_group(config_group)

    log_group = OptionGroup(self, "logging options")
    log_group.add_option('-l', '--log-level', metavar='N',
      dest='logthresh',
      type='int',
      default=3,
      help="specify a level (0-6) of verbosity for the output log")
    log_group.add_option('--log-file', metavar='PATH',
      dest='logfile',
      default=None,
      help="specify a file in which to log output")
    self.add_option_group(log_group)
  
    library_group = OptionGroup(self, "library options")
    library_group.add_option('--lib-path', metavar='PATH',
      action='append',
      dest='libpath',
      default=[],
      help="specify directory containing deploy library files")
    library_group.add_option('--share-path', metavar='PATH',
      action='append',
      dest='sharepath',
      default=[],
      help="specify directory containing deploy shared files")
    self.add_option_group(library_group)
  
    module_group = OptionGroup(self, "module options")
    module_group.add_option('--force', metavar='MODULE',
      action='append',
      dest='force_modules',
      default=[],
      help="force a module's events to execute")
    module_group.add_option('--skip', metavar='MODULE',
      action='append',
      dest='skip_modules',
      default=[],
      help="skip execution of a module's events")
    module_group.add_option('--enable', metavar='MODULE',
      action='append',
      dest='enabled_modules',
      default=[],
      help='enable a module')
    module_group.add_option('--disable', metavar='MODULE',
      action='append',
      dest='disabled_modules',
      default=[],
      help='disable a module')
    self.add_option_group(module_group)

    event_group = OptionGroup(self, "event options")
    event_group.add_option('--list-events',
      action='store_true',
      default=False,
      dest='list_events',
      help='list all events for the specified definition')
    event_group.add_option('--force-event', metavar='EVENT',
      action='append',
      dest='force_events',
      default=[],
      help="force an individual event")
    event_group.add_option('--skip-event', metavar='EVENT',
      action='append',
      dest='skip_events',
      default=[],
      help="skip an individual event")
    self.add_option_group(event_group)
