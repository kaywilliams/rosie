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
import re

BOOLEANS_TRUE  = ['True', 'true', 'Yes', 'yes', 'On', 'on', '1']
BOOLEANS_FALSE = ['False', 'false', 'No', 'no', 'Off', 'off', '0']

RPM_GLOB  = '*.[Rr][Pp][Mm]'
SRPM_GLOB = '*.[Ss][Rr][Cc].[Rr][Pp][Mm]'

RPM_REGEX  = re.compile('.*\.[Rr][Pp][Mm]')
SRPM_REGEX = re.compile('.*\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]')

RPM_PNVRA_REGEX  = re.compile('(?P<path>.*/)?'  # all chars up to the last '/'
                              '(?P<name>.+)'    # rpm name
                              '-'
                              '(?P<version>.+)' # rpm version
                              '-'
                              '(?P<release>.+)' # rpm release
                              '\.'
                              '(?P<arch>.+)'    # rpm architecture
                              '\.[Rr][Pp][Mm]')
SRPM_PNVRA_REGEX = re.compile('(?P<path>.*/)?'  # all chars up to the last '/'
                              '(?P<name>.+)'    # srpm name
                              '-'
                              '(?P<version>.+)' # srpm version
                              '-'
                              '(?P<release>.+)' # srpm release
                              '\.([Ss][Rr][Cc])\.[Rr][Pp][Mm]')

# list of all currently-known kernel package equivalents
KERNELS = [ 'kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
            'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
            'kernel-BOOT' ]
