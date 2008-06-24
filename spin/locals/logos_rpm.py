from spin.locals import LocalsDict, REMOVE

__all__ = ['L_LOGOS_RPM_DISTRO_INFO']

DEFAULT_DISTRO_INFO = {
  'folder': 'centos5',
  'start_color': (33, 85, 147),
  'end_color': (30, 81, 140),
  'triggerin': {
    'kdebase': '''KSPLASHRC=/usr/share/config/ksplashrc
if [ -e $KSPLASHRC -a ! -e $KSPLASHRC.rpmsave ]; then
  %%{__mv} -f $KSPLASHRC $KSPLASHRC.rpmsave
fi
cat > $KSPLASHRC <<EOF
[KSplash]
Theme=Spin
EOF
''',
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
    'kdebase': '''KSPLASHRC=/usr/share/config/ksplashrc
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $KSPLASHRC.rpmsave ]; then
    %%{__rm} -f $KSPLASHRC
    %%{__mv} $KSPLASHRC.rpmsave $KSPLASHRC
  fi
fi
''',
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

L_LOGOS_RPM_DISTRO_INFO = {
  'Fedora': LocalsDict({
    '0': DEFAULT_DISTRO_INFO,
    '8': {
      'post-install': '''SPIN_BACKGROUNDS="1-spin-sunrise.png 2-spin-day.png 3-spin-sunset.png 4-spin-night.png"
DEFAULT=/usr/share/backgrounds/spin/default.jpg
for file in $SPIN_BACKGROUNDS; do
  if [ -e /usr/share/backgrounds/spin/$file ]; then
    %{__rm} -f /usr/share/backgrounds/spin/$file
  fi
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
DEFAULTS="default-5_4.png default.jpg default.png default-wide.png"
for default in $DEFAULTS; do
  file=$BACKGROUNDS/images/$default
  if [ -e $file ]; then
    %%{__mv} $file $file.rpmsave
    %%{__ln_s} $BACKGROUNDS/spin/$default $file
  fi
done
if [ -e $BACKGROUNDS/infinity ]; then
  %%{__mv} $BACKGROUNDS/infinity $BACKGROUNDS/infinity.rpmsave
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
      'triggerin': {
        'desktop-backgrounds-compat': '''BACKGROUNDS=/usr/share/backgrounds
DEFAULTS="default.jpg default.png default-wide.png default-5_4.png"
for default in $DEFAULTS; do
  file=$BACKGROUNDS/images/$default
  if [ -e $file ]; then
    %%{__mv} $file $file.rpmsave
    %%{__ln_s} $BACKGROUNDS/spin/$default $file
  fi
default=$BACKGROUNDS/default.png
if [ -e $default ]; then
  %%{__mv} $default $default.rpmsave
  %%{__ln_s} $BACKGROUNDS/spin/default.jpg $default
fi
done
''',
        'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
if [ -e $BACKGROUNDS/waves -a ! -e $BACKGROUNDS/waves.rpmsave ]; then
  %%{__mv} $BACKGROUNDS/waves $BACKGROUNDS/waves.rpmsave
  %%{__ln_s} $BACKGROUNDS/spin $BACKGROUNDS/waves
  if [ ! -e $BACKGROUNDS/spin/waves.xml ]; then
    %%{__ln_s} $BACKGROUNDS/spin/spin.xml $BACKGROUNDS/spin/waves.xml
  fi
  for wave in `ls -1 $BACKGROUNDS/waves.rpmsave | grep png`; do
    %%{__ln_s} $BACKGROUNDS/spin/default.png $BACKGROUNDS/waves/$wave
  done
fi
''',
      },
      'triggerun': {
        'desktop-backgrounds-compat': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  for default in `ls -1 $BACKGROUNDS/images/default* | grep -v "rpmsave"`; do
    %%{__rm} -f $default
    %%{__mv} -f $default.rpmsave $default
  done
  default=$BACKGROUNDS/default.png
  if [ -e $default.rpmsave ]; then
    %%{__rm} -f $default
    %%{__mv} -f $default.rpmsave $default
  fi
fi
''',
        'desktop-backgrounds-basic': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  %%{__rm} -rf $BACKGROUNDS/waves
  %%{__mv} -f $BACKGROUNDS/waves.rpmsave $BACKGROUNDS/waves
  %%{__rm} -f $BACKGROUNDS/spin/waves.xml
fi
''',
      },
    },
  }),
  'CentOS': LocalsDict({
    '0': DEFAULT_DISTRO_INFO,
  }),
  'Fedora Core': LocalsDict({
    '0': DEFAULT_DISTRO_INFO,
  }),
  'Red Hat Enterprise Linux Server': LocalsDict({
    '0': DEFAULT_DISTRO_INFO,
    '5': {
      'folder': 'redhat5',
      'start_color': (120, 30, 29),
      'end_color': (88, 23, 21),
    },
  }),
  '*': LocalsDict({
    '0': DEFAULT_DISTRO_INFO,
  }),
}
