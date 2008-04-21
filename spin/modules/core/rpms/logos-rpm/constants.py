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
__all__ = ['XWINDOW_MAPPING', 'DISTRO_INFO']

API_VERSION = 5.0

XWINDOW_MAPPING = {
  'all':   ['gnome', 'kde', 'required'],
  'gnome': ['gnome', 'required'],
  'kde':   ['kde', 'required'],
  'none':  ['required'],
}

DISTRO_INFO = {
  'CentOS': {
    '5': {
      'folder': 'c5',
      'start_color': (33, 85, 147),
      'end_color': (30, 81, 140),
    }
  },
  'Fedora Core': {
    '6': {
      'folder':'f6',
      'start_color': (0, 37, 77),
      'end_color': (0, 32, 68),
    }
  },
  'Fedora': {
    '7': {
      'folder': 'f7',
      'start_color': (0, 27, 82),
      'end_color': (28, 41, 89),
    },
    '8': {
      'folder': 'f8',
      'start_color': (32, 75, 105),
      'end_color': (70, 110, 146)
    },
    '9': {
      ## UPDATEME
      'folder': 'f8',
      'start_color': (32, 75, 105),
      'end_color': (70, 110, 146)
    },
  },
  'Red Hat Enterprise Linux Server': {
    '5': {
      'folder': 'r5',
      'start_color': (120, 30, 29),
      'end_color': (88, 23, 21)
    }
  },
  '*': { # default
    '0': {
      'folder': 'r5',
      'start_color': (120, 30, 29),
      'end_color': (88, 23, 21)
    }
  }
}
