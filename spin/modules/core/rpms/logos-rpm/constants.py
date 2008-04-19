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
      'start_color': (),
      'end_color': (),
    }
  },
  'Fedora Core': {
    '6': {
      'folder':'f6',
      'start_color': (),
      'end_color': (),
    }
  },
  'Fedora': {
    '7': {
      'folder': 'f7',
      'start_color': (),
      'end_color': (),
    },
    '8': {
      'folder': 'f8',
      'start_color': (),
      'end_color': ()
    },
    '9': {
      'folder': 'f8',
      'start_color': (),
      'end_color': ()
    },
  },
  'Red Hat Enterprise Linux Server': {
    '5': {
      'folder': 'r5',
      'start_color': (),
      'end_color': ()
    }
  },
  '*': { # default
    '0': {
      'folder': 'r5',
      'start_color': (),
      'end_color': ()
    }
  }
}
