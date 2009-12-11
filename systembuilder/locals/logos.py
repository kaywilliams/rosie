from systembuilder.locals import LocalsDict, REMOVE

__all__ = ['L_LOGOS']

L_LOGOS = LocalsDict({
  "anaconda-0": {
    'splash-image': dict(filename='syslinux-splash.png', format='lss')
  },
  "anaconda-11.2.0.66-1": { # no longer converts png to lss
    'splash-image': dict(filename='syslinux-vesa-splash.jpg', format='jpg')
  },
  "anaconda-11.3.0.36-1": {
    'splash-image': dict(filename='syslinux-vesa-splash.jpg', format='png',
                         output='splash.jpg')
  }
})
