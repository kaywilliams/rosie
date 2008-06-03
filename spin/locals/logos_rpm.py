from spin.locals import LocalsDict, REMOVE

__all__ = ['L_LOGOS_RPM_FILES', 'L_LOGOS_RPM_INFO']

L_LOGOS_RPM_FILES = LocalsDict({
  "anaconda-0": {
    '/usr/share/apps/kdm/themes/Spin/background.png' : dict(
      xwindow_type = 'kde',
      image_width  = 2560,
      image_height = 1600,
    ),
    '/usr/share/apps/kdm/themes/Spin/innerbackground.png': dict(
      xwindow_type = 'kde',
      image_width  = 680,
      image_height = 520,
    ),
    '/usr/share/apps/kdm/themes/Spin/screenshot.png': dict(
      xwindow_type = 'kde',
      image_width  = 1024,
      image_height = 768,
    ),
    '/usr/share/backgrounds/spin/default.jpg': dict(
      xwindow_type = 'gnome',
      image_width  = 1600,
      image_height = 1200,
    ),
    '/usr/share/backgrounds/spin/default-5_4.jpg': dict(
      xwindow_type = 'gnome',
      image_width  = 1280,
      image_height = 1024,
    ),
    '/usr/share/backgrounds/spin/default-dual.jpg': dict(
      xwindow_type = 'gnome',
      image_width  = 2560,
      image_height = 1240,
    ),
    '/usr/share/backgrounds/spin/default-dual-wide.jpg': dict(
      xwindow_type = 'gnome',
      image_width  = 2560,
      image_height = 960,
    ),
    '/usr/share/backgrounds/spin/default-wide.jpg': dict(
      xwindow_type = 'gnome',
      image_width  = 1680,
      image_height = 1050,
    ),
    '/usr/share/gdm/themes/Spin/background.png': dict(
      xwindow_type = 'gnome',
      image_width  = 2560,
      image_height = 1600,
    ),
    '/usr/share/gdm/themes/Spin/innerbackground.png': dict(
      xwindow_type = 'gnome',
      image_width  = 680,
      image_height = 520,
    ),
    '/usr/share/gdm/themes/Spin/screenshot.png': dict(
      xwindow_type = 'gnome',
      image_width  = 1024,
      image_height = 768,
    ),
    '/usr/share/gnome-screensaver/lock-dialog-system.png': dict(
      xwindow_type = 'gnome',
      image_width  = 400,
      image_height = 314,
    ),
    '/usr/lib/anaconda-runtime/boot/syslinux-splash.png': dict(
      xwindow_type = 'required',
      image_width  = 640,
      image_height = 300,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          text_coords = (320, 10),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          font_size = 12,
          text_coords = (320, 30),
        ),
      ]
    ),
    '/usr/share/anaconda/pixmaps/syslinux-splash.png': dict(
      xwindow_type = 'required',
      image_width  = 640,
      image_height = 300,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          text_coords = (320, 10),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          font_size = 12,
          text_coords = (320, 30),
        ),
      ]
    ),
    '/usr/share/anaconda/pixmaps/anaconda_header.png': dict(
      xwindow_type = 'required',
      image_width  = 800,
      image_height = 88,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 18,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (400, 38),
          text_max_width = 700
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (720, 65),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/progress_first-lowres.png': dict(
      xwindow_type = 'required',
      image_width  = 350,
      image_height = 224,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 18,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (100, 180),
          text_max_width = 180,
        ),
        dict(
          text = 'Version %(version)s',
          font_size = 9,
          font_color = 'white',
          text_coords = (210, 110),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (175, 215),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/progress_first.png': dict(
      xwindow_type = 'required',
      image_width  = 443,
      image_height = 284,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 18,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (170, 240),
          text_max_width = 320,
        ),
        dict(
          text = 'Version %(version)s',
          font_size = 12,
          font_color = 'white',
          text_coords = (290, 140),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (220, 270),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/rnotes/welcome.png': dict(
      xwindow_type = 'required',
      image_width  = 600,
      image_height = 284,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 18,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (180, 240),
          text_max_width = 350,
        ),
        dict(
          text = 'Version %(version)s',
          font_size = 11,
          font_color = 'white',
          text_coords = (420, 140),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (300, 265),
        )
      ]
    ),
    '/usr/share/anaconda/pixmaps/splash.png': dict(
      xwindow_type = 'required',
      image_width  = 600,
      image_height = 284,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 18,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (180, 240),
          text_max_width = 350,
        ),
        dict(
          text = 'Version %(version)s',
          font_size = 11,
          font_color = 'white',
          text_coords = (420, 140),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (300, 265),
        )
      ]
    ),
    '/usr/share/apps/ksplash/Themes/Spin/Preview.png': dict(
      xwindow_type = 'kde',
      image_width  = 399,
      image_height = 322,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (269, 252),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (289, 267),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (200, 322),
        )
      ]
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_active_bar.png': dict(
      xwindow_type = 'kde',
      image_width  = 400,
      image_height = 64,
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_bottom.png': dict(
      xwindow_type = 'kde',
      image_width  = 400,
      image_height = 19,
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_inactive_bar.png': dict(
      xwindow_type = 'kde',
      image_width  = 400,
      image_height = 64,
    ),
    '/usr/share/apps/ksplash/Themes/Spin/splash_top.png': dict(
      xwindow_type = 'kde',
      image_width  = 400,
      image_height = 248,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (270, 188),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (290, 203),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (200, 238),
        )
      ]
    ),
    '/usr/share/firstboot/pixmaps/firstboot-left.png': dict(
      xwindow_type = 'required',
      image_width  = 160,
      image_height = 600,
    ),
    '/usr/share/firstboot/pixmaps/splash-small.png': dict(
      xwindow_type = 'required',
      image_width  = 364,
      image_height = 259,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (254, 179),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (274, 194),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (182, 249),
        )
      ]
    ),
    '/usr/share/pixmaps/poweredby.png': dict(
      xwindow_type = 'required',
      image_width  = 88,
      image_height = 31,
    ),
    '/usr/share/pixmaps/splash/gnome-splash.png': dict(
      xwindow_type = 'gnome',
      image_width  = 420,
      image_height = 293,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (300, 213),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (320, 238),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (210, 283),
        )
      ]
    ),
    '/usr/share/rhgb/main-logo.png': dict(
      xwindow_type = 'required',
      image_width  = 799,
      image_height = 399,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (659, 299),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (679, 319),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (400, 389),
        )
      ]
    ),
    '/boot/grub/grub-splash.png': dict(
      xwindow_type = 'required',
      image_width  = 640,
      image_height = 480,
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_size_min = 9,
          font_color = 'white',
          text_coords = (450, 360),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 9,
          font_color = 'white',
          text_coords = (490, 375),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (320, 470),
        )
      ]
    ),
  },
  "anaconda-11.2.0.66-1": {
    '/usr/lib/anaconda-runtime/boot/syslinux-splash.png': REMOVE,
    '/usr/share/anaconda/pixmaps/syslinux-splash.png': dict(
      image_width  = 640,
      image_height = 480,
    ),
    '/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg': dict(
      xwindow_type = 'required',
      image_width  = 640,
      image_height = 480,
      image_format = 'JPEG',
      strings = [
        dict(
          text = '%(fullname)s',
          font = 'DejaVuLGCSans-Bold.ttf',
          font_size = 14,
          font_color = 'white',
          text_coords = (500, 180),
          text_max_width = 140,
        ),
        dict(
          text = 'Version %(version)s',
          halign = 'right',
          font_size = 12,
          font_color = 'white',
          text_coords = (540, 195),
        ),
        dict(
          text = '%(copyright)s',
          font_size = 9,
          font_color = '#9d9d9d',
          text_coords = (320, 290),
        )
      ],
    ),
  },
  "anaconda-11.3.0.36-1": {
    '/usr/lib/anaconda-runtime/syslinux-vesa-splash.jpg': dict(
      xwindow_type = 'required',
      image_width  = 640,
      image_height = 480,
      image_format = 'PNG',
    ),
  },
})

DEFAULT_INFO = {
  'folder': 'centos5',
  'start_color': (33, 85, 147),
  'end_color': (30, 81, 140),
  'limited_palette_font_color': 8,
  'triggerin': {
    'gdm': '''CUSTOM_CONF=%%{_sysconfdir}/gdm/custom.conf
THEME_CONF=/usr/share/%(rpm_name)s/custom.conf
%%{__mv} -f $CUSTOM_CONF $CUSTOM_CONF.rpmsave
%%{__cp} $THEME_CONF $CUSTOM_CONF
''',
    'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
DEFAULTS="default-5_4.jpg default-dual.jpg default-dual-wide.jpg default.jpg default-wide.jpg"
for default in $DEFAULTS; do
  file=$BACKGROUNDS/images/$default
  if [ -e $file ]; then
    %%{__mv} $file $file.rpmsave
    %%{__ln_s} $BACKGROUNDS/spin/$default $file
  fi
done
''',
    'rhgb': '''RHGB_FOLDER=/usr/share/rhgb
if [ -e $RHGB_FOLDER/large-computer.png ]; then
  if [ ! -e $RHGB_FOLDER/large-computer.png.rpmsave ]; then
    %%{__mv} $RHGB_FOLDER/large-computer.png $RHGB_FOLDER/large-computer.png.rpmsave
  fi
  if [ -e $RHGB_FOLDER/large-computer.png ]; then
    %%{__rm} -f $RHGB_FOLDER/large-computer.png
  fi
  %%{__ln_s} $RHGB_FOLDER/main-logo.png $RHGB_FOLDER/large-computer.png
fi
''',
  },
  'triggerun': {
    'gdm': '''CUSTOM_CONF=%%{_sysconfdir}/gdm/custom.conf
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  %%{__rm} -f $CUSTOM_CONF.rpmsave
fi
''',
    'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  for default in `ls -1 $BACKGROUNDS/images/default* | grep -v "rpmsave"`; do
    %%{__rm} -f $default
    %%{__mv} -f $default.rpmsave $default
  done
fi
''',
    'rhgb': '''RHGB_FOLDER=/usr/share/rhgb
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $RHGB_FOLDER/large-computer.png.rpmsave ]; then
    %%{__rm} -f $RHGB_FOLDER/large-computer.png
    %%{__mv} $RHGB_FOLDER/large-computer.png.rpmsave $RHGB_FOLDER/large-computer.png
  fi
fi
''',
  },
}

L_LOGOS_RPM_INFO = {
  'Fedora': LocalsDict({
    '0': DEFAULT_INFO,
    '8': {
      'post-install': '''SPIN_BACKGROUNDS="1-spin-sunrise.png 2-spin-day.png 3-spin-sunset.png 4-spin-night.png"
DEFAULT=/usr/share/backgrounds/spin/default.jpg
for file in $SPIN_BACKGROUNDS; do
  %{__ln_s} $DEFAULT /usr/share/backgrounds/spin/$file
done
''',
      'post-uninstall': '''SPIN_BACKGROUNDS="1-spin-sunrise.png 2-spin-day.png 3-spin-sunset.png 4-spin-night.png"
for file in $SPIN_BACKGROUNDS; do
  %{__rm} -f /usr/share/backgrounds/spin/$file
done
''',
      'triggerin': {
        'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
DEFAULTS="default-5_4.jpg default-dual.jpg default-dual-wide.jpg default.jpg default-wide.jpg"
for default in $DEFAULTS; do
  file=$BACKGROUNDS/images/$default
  if [ -e $file ]; then
    %%{__mv} $file $file.rpmsave
    %%{__ln_s} $BACKGROUNDS/spin/$default $file
  fi
done
if [ -e $BACKGROUNDS/infinity ]; then
  %%{__mv} $BACKGROUNDS/infinity $BACKGROUNDS/infinity.rpmsave,
  %%{__ln_s} $BACKGROUNDS/spin $BACKGROUNDS/infinity
  if [ ! -e $BACKGROUNDS/spin/infinity.xml ]; then
    %%{__ln_s} $BACKGROUNDS/spin/spin.xml $BACKGROUNDS/spin/infinity.xml
  fi
fi
'''
      },
      'triggerun': {
        'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  for default in `ls -1 $BACKGROUNDS/images/default* | grep -v "rpmsave"`; do
    %%{__rm} -f $default
    %%{__mv} -f $default.rpmsave $default
  done
  %%{__rm} -rf $BACKGROUNDS/infinity
  %%{__mv} -f $BACKGROUNDS/infinity.rpmsave $BACKGROUNDS/infinity
  %%{__rm} -f $BACKGROUNDS/spin/infinity.xml
fi
''',
      },
    },
    '9': {
      'folder': 'fedora9',
      'start_color': (32, 75, 105),
      'end_color': (70, 110, 146),
      'limited_palette_font_color': 13,
      'triggerin': {
        'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
DEFAULTS="default-5_4.jpg default-dual.jpg default-dual-wide.jpg default.jpg default-wide.jpg"
for default in $DEFAULTS; do
  file=$BACKGROUNDS/images/$default
  if [ -e $file ]; then
    %%{__mv} $file $file.rpmsave
    %%{__ln_s} $BACKGROUNDS/spin/$default $file
  fi
done
if [ -e $BACKGROUNDS/waves ]; then
  %%{__mv} $BACKGROUNDS/waves $BACKGROUNDS/waves.rpmsave,
  %%{__ln_s} $BACKGROUNDS/spin $BACKGROUNDS/waves
  if [ ! -e $BACKGROUNDS/spin/waves.xml ]; then
    %%{__ln_s} $BACKGROUNDS/spin/spin.xml $BACKGROUNDS/spin/waves.xml
  fi
fi
'''
      },
      'triggerun': {
        'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  for default in `ls -1 $BACKGROUNDS/images/default* | grep -v "rpmsave"`; do
    %%{__rm} -f $default
    %%{__mv} -f $default.rpmsave $default
  done
  %%{__rm} -rf $BACKGROUNDS/waves
  %%{__mv} -f $BACKGROUNDS/waves.rpmsave $BACKGROUNDS/waves
  %%{__rm} -f $BACKGROUNDS/spin/waves.xml
fi
''',
      },
    },
  }),
  'CentOS': LocalsDict({
    '0': DEFAULT_INFO,
  }),
  'Fedora Core': LocalsDict({
    '0': DEFAULT_INFO,
  }),
  'Red Hat Enterprise Linux Server': LocalsDict({
    '0': DEFAULT_INFO,
    '5': {
      'folder': 'redhat5',
      'start_color': (120, 30, 29),
      'end_color': (88, 23, 21),
      'limited_palette_font_color': 0,
    },
  }),
  '*': LocalsDict({
    '0': DEFAULT_INFO,
  }),
}
