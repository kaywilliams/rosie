from dimsbuild.event     import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib       import RpmBuildHook, RpmsInterface
from rpmlocals import SCRIPT

EVENTS = [
  {
    'id':        'default-theme-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent':    'RPMS',
  },
]

HOOK_MAPPING = {
  'DefaultThemeHook': 'default-theme-rpm',
  'ValidateHook'    : 'validate',
}

API_VERSION = 4.0

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_theme.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/rpms/default-theme-rpm',
                            schemafile='default-theme-rpm.rng')


class DefaultThemeHook(RpmBuildHook):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_theme.default-theme-rpm'
    
    data = {
      'config': [
        '/distro/rpms/default-theme-rpm',
      ],
      'output': [],
    }

    self.themename = interface.config.get(
      '/distro/rpms/default-theme-rpm/theme/text()',
      interface.product
    )

    RpmBuildHook.__init__(self, interface, data, 'default-theme-rpm',
                          '%s-default-theme' % interface.product,
                          summary='Script to set default gdm graphical '
                          'theme', description='The %s-default-theme '
                          'package requires the gdm package. Its sole '
                          'function is to modify the value of the '
                          'GraphicalTheme attribute in '
                          '/usr/share/gdm/defaults.conf to the %s '
                          'theme.' %(interface.product, self.themename,),
                          requires='gdm',
                          condrequires='gdm',
                          package_type='conditional',
                          default=False)
  
  def _get_post_install(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(SCRIPT % self.themename)
    f.close()
    return 'postinstall.sh'
