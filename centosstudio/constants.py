#
# Copyright (c) 2011
# CentOS Studio Foundation. All rights reserved.
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

BOOLEANS_TRUE  = ['true',  'yes', 'on',  '1']
BOOLEANS_FALSE = ['false', 'no',  'off', '0']

RPM_GLOB  = '*.[Rr][Pp][Mm]'
SRPM_GLOB = '*.[Ss][Rr][Cc].[Rr][Pp][Mm]'

RPM_REGEX  = '.*\.[Rr][Pp][Mm]'
SRPM_REGEX = '.*\.[Ss][Rr][Cc]\.[Rr][Pp][Mm]'

# list of all currently-known kernel package equivalents
KERNELS = [ 'kernel', 'kernel-smp', 'kernel-zen', 'kernel-zen0',
            'kernel-enterprise', 'kernel-hugemem', 'kernel-bigmem',
            'kernel-BOOT' ]
