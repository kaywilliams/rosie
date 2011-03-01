#
# Copyright (c) 2011
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
import textwrap

from optparse import HelpFormatter, OptionGroup

class CleanHelpFormatter(HelpFormatter):
  """Cleaner version of the optparse default help formatter"""

  def __init__(self,
               indent_increment=2,
               max_help_position=24,
               width=79,
               short_first=1):
    HelpFormatter.__init__(self, indent_increment, max_help_position, width, short_first)

  def format_usage(self, usage):
    return "usage: %s\n" % usage

  def format_heading(self, heading):
    return "%*s%s:\n" % (self.current_indent, "", heading)

#  def format_description(self, description):
#    desc = HelpFormatter.format_description(self, description)
#    desc += "\n"
#    return desc

  def format_option_strings(self, option):
    """Return a comma-separated list of option strings"""
    short_opts = option._short_opts
    long_opts = option._long_opts

    if self.short_first:
      opts = short_opts + long_opts
    else:
      opts = long_opts + short_opts

    # the following code allows options to specify metavars that display
    # on the screen even if they wouldn't ordinarily do so (callbacks, in
    # particular
    if option.metavar:
      metavar = option.metavar
    elif option.takes_value():
      metavar = option.dest.upper()
    else:
      metavar = None

    if metavar is not None:
      return ", ".join(opts) + " " + metavar
    else:
      return ", ".join(opts)


class OptionGroupId(OptionGroup):
  """Defines an OptionGroup with an id field for better unique identification.
  If I'm feeling cool one day I'll make it so that a parser can't have more
  than one of each id.  Right now that's up to the implementer to enforce.  If
  two OptionGroupIds are added with the same ID, the behavior is determinstically
  undefined.

  This makes it possible for someone to come along and add more options to an
  already existing group if he knows it's id.
  """

  def __init__(self, parser, title, id):
    OptionGroup.__init__(self, parser, title)
    self.id = id
