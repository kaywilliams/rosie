from spin.locals import LocalsDict, REMOVE

__all__ = ['L_LOGOS_RPM_APPLIANCE_INFO']

DEFAULT_APPLIANCE_INFO = {
  'applianceid': 'centos5',
  'background': (33, 85, 147),
  'triggers': {
    'kdebase': {
      'triggerin': '''KSPLASHRC=/usr/share/config/ksplashrc
if [ -e $KSPLASHRC -a ! -e $KSPLASHRC.rpmsave ]; then
  %%{__mv} -f $KSPLASHRC $KSPLASHRC.rpmsave
fi
cat > $KSPLASHRC <<EOF
[KSplash]
Theme=Spin
EOF
''',
      'triggerun': '''KSPLASHRC=/usr/share/config/ksplashrc
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $KSPLASHRC.rpmsave ]; then
    %%{__rm} -f $KSPLASHRC
    %%{__mv} $KSPLASHRC.rpmsave $KSPLASHRC
  fi
fi
''',
    },
    'gdm': {
      'triggerin': '''CUSTOM_CONF=%%{_sysconfdir}/gdm/custom.conf
THEME_CONF=/usr/share/%(rpm_name)s/custom.conf
%%{__mv} -f $CUSTOM_CONF $CUSTOM_CONF.rpmsave
%%{__cp} $THEME_CONF $CUSTOM_CONF
''',
      'triggerun': '''CUSTOM_CONF=%%{_sysconfdir}/gdm/custom.conf
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  %%{__rm} -f $CUSTOM_CONF.rpmsave
fi
''',
    },
    'desktop-backgrounds-basic': {
      'triggerin': '''BACKGROUNDS=/usr/share/backgrounds
DEFAULTS="default-5_4.jpg default-dual.jpg default-dual-wide.jpg default.jpg default-wide.jpg"
for default in $DEFAULTS; do
  file=$BACKGROUNDS/images/$default
  if [ -e $file ]; then
    %%{__mv} $file $file.rpmsave
    %%{__ln_s} $BACKGROUNDS/spin/$default $file
  fi
done
''',
      'triggerun': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  for default in `ls -1 $BACKGROUNDS/images/default* | grep -v "rpmsave"`; do
    %%{__rm} -f $default
    %%{__mv} -f $default.rpmsave $default
  done
fi
''',
    },
    'rhgb': {
      'triggerin': '''RHGB_FOLDER=/usr/share/rhgb
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
      'triggerun': '''RHGB_FOLDER=/usr/share/rhgb
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $RHGB_FOLDER/large-computer.png.rpmsave ]; then
    %%{__rm} -f $RHGB_FOLDER/large-computer.png
    %%{__mv} $RHGB_FOLDER/large-computer.png.rpmsave $RHGB_FOLDER/large-computer.png
  fi
fi
''',
    },
  },
}

FEDORA_APPLIANCE_INFO = DEFAULT_APPLIANCE_INFO.copy()
FEDORA_APPLIANCE_INFO.update({
  'applianceid': 'fedora9',
  'background': (32, 75, 105),
})

L_LOGOS_RPM_APPLIANCE_INFO = {
  'Fedora': LocalsDict({
    '0': FEDORA_APPLIANCE_INFO,
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
      'triggers': {
        'desktop-backgrounds-basic': {
          'triggerin': '''BACKGROUNDS=/usr/share/backgrounds
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
''',
      'triggerun': '''BACKGROUNDS=/usr/share/backgrounds
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
    },
    '9': {
      'triggers': {
        'desktop-backgrounds-compat': {
          'triggerin': '''BACKGROUNDS=/usr/share/backgrounds
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
          'triggerun': '''BACKGROUNDS=/usr/share/backgrounds
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
        },
        'firstboot': {
          'triggerin': '''THEME_DIR=/usr/share/firstboot/themes
if [ ! -e $THEME_DIR/default.rpmsave ]; then
  %%{__mv} $THEME_DIR/default $THEME_DIR/default.rpmsave
  %%{__cp} -rf $THEME_DIR/spin $THEME_DIR/default
  for file in `ls -1 $THEME_DIR/default.rpmsave`; do
    if [ ! -e $THEME_DIR/default/$file ]; then
      %%{__cp} $THEME_DIR/default.rpmsave/$file $THEME_DIR/default/$file
    fi
  done
fi
''',
          'triggerun': '''THEME_DIR=/usr/share/firstboot/themes
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $THEME_DIR/default.rpmsave ]; then
    %%{__rm} -rf $THEME_DIR/default
    %%{__mv} $THEME_DIR/default.rpmsave $THEME_DIR/default
  fi
fi
''',
        },
        'desktop-backgrounds-basic': {
          'triggerin': '''BACKGROUNDS=/usr/share/backgrounds
if [ ! -e $BACKGROUNDS/waves.rpmsave ]; then
  %%{__mv} $BACKGROUNDS/waves $BACKGROUNDS/waves.rpmsave
  %%{__ln_s} $BACKGROUNDS/spin $BACKGROUNDS/waves
  if [ ! -e $BACKGROUNDS/spin/waves.xml ]; then
    %%{__ln_s} $BACKGROUNDS/spin/spin.xml $BACKGROUNDS/spin/waves.xml
  fi
fi
for wave in `ls -1 $BACKGROUNDS/waves.rpmsave | grep png`; do
  if [ ! -e $BACKGROUNDS/waves/$wave ]; then
    %%{__ln_s} $BACKGROUNDS/spin/default.png $BACKGROUNDS/waves/$wave
  fi
done
''',
          'triggerun': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $BACKGROUNDS/waves.rpmsave ]; then
    for wave in `ls -1 $BACKGROUNDS/waves.rpmsave | grep png`; do
      %%{__rm} -f $BACKGROUNDS/waves/$wave
    done
    %%{__rm} -f $BACKGROUNDS/waves
    %%{__mv} -f $BACKGROUNDS/waves.rpmsave $BACKGROUNDS/waves
    %%{__rm} -f $BACKGROUNDS/spin/waves.xml
  fi
fi
''',
        },
        'kde-settings': {
          'triggerin': '''CONFIG_DIR=/usr/share/kde-settings/kde-profile/default/share/config
if [ ! -e $CONFIG_DIR/ksplashrc.rpmsave ]; then
  %%{__cp} $CONFIG_DIR/ksplashrc $CONFIG_DIR/ksplashrc.rpmsave
fi
%%{__sed} -i 's|FedoraWaves|Spin|g' $CONFIG_DIR/ksplashrc
''',
          'triggerun': '''CONFIG_DIR=/usr/share/kde-settings/kde-profile/default/share/config
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $CONFIG_DIR/ksplashrc.rpmsave ]; then
    %%{__rm} -f $CONFIG_DIR/ksplashrc
    %%{__mv} -f $CONFIG_DIR/ksplashrc.rpmsave $CONFIG_DIR/ksplashrc
  fi
fi
''',
        },
        'kde-settings-kdm': {
          'triggerin': '''CONFIG_DIR=/etc/kde/kdm
if [ ! -e $CONFIG_DIR/kdmrc.rpmsave ]; then
  %%{__cp} $CONFIG_DIR/kdmrc $CONFIG_DIR/kdmrc.rpmsave
fi
%%{__sed} -i 's|FedoraWaves|Spin|g' $CONFIG_DIR/kdmrc
''',
          'triggerun': '''CONFIG_DIR=/etc/kde/kdm
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  if [ -e $CONGIG_DIR/kdmrc.rpmsave ]; then
    %%{__rm} -f $CONFIG_DIR/kdmrc
    %%{__mv} -f $CONFIG_DIR/kdmrc.rpmsave $CONFIG_DIR/kdmrc
  fi
fi
''',
        },
      },
    },
  }),
  'CentOS': LocalsDict({
    '0': DEFAULT_APPLIANCE_INFO,
  }),
  'Fedora Core': LocalsDict({
    '0': DEFAULT_APPLIANCE_INFO,
  }),
  'Red Hat Enterprise Linux Server': LocalsDict({
    '0': DEFAULT_APPLIANCE_INFO,
    '5': {
      'applianceid': 'redhat5',
      'background': (120, 30, 29),
      'triggers': {
        'desktop-backgrounds-basic': {
          'triggerin': '''BACKGROUNDS=/usr/share/backgrounds
DEFAULTS="default-5_4.jpg default-dual.jpg default-dual-wide.jpg default.jpg default-wide.jpg"
for default in $DEFAULTS; do
  %%{__ln_s} $BACKGROUNDS/spin/$default $BACKGROUNDS/images/$default
done
''',
          'triggerun': '''BACKGROUNDS=/usr/share/backgrounds
if [ "$2" -eq "0" -o "$1" -eq "0" ]; then
  for default in `ls -1 $BACKGROUNDS/images/default*`; do
    %%{__rm} -f $default
  done
fi
''',
        },
      },
    },
  }),
  '*': LocalsDict({
    '0': DEFAULT_APPLIANCE_INFO,
  }),
}
