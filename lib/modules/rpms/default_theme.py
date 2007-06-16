from os.path import join

from event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from rpms.lib import RpmsHandler, RpmsInterface

EVENTS = [
  {
    'id': 'default-theme-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS', 
  },
]

HOOK_MAPPING = {
  'DefaultThemeHook': 'default-theme-rpm',
}

API_VERSION = 4.0

class DefaultThemeHook(RpmsHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_theme.default-theme-rpm'
    self.eventid = 'default-theme-rpm'
    
    data = {
      'config': [
        '//rpms/default-theme-rpm',
      ],
      'output': [
        join(interface.METADATA_DIR, 'default-theme-rpm/'),
      ],
    }

    self.themename = interface.config.get('//rpms/default-theme-rpm/theme/text()', interface.product)

    RpmsHandler.__init__(self, interface, data,
                         elementname='default-theme-rpm',
                         rpmname='%s-default-theme' %(interface.product,),
                         requires='gdm',
                         description='Script to set default gdm graphical theme',
                         long_description='The %s-default-theme package requires the gdm package. '
                         ' Its sole function is to modify the value of the GraphicalTheme attribute in'
                         ' /usr/share/gdm/defaults.conf to the %s theme' %(interface.product,
                                                                           self.themename,))
  def apply(self):
    RpmsHandler.apply(self, type='conditional', requires='gdm')
    
  def get_post_install_script(self):
    f = open(join(self.output_location, 'postinstall.sh'), 'w')
    f.write(SCRIPT %(self.themename,))
    f.close()
    return 'postinstall.sh'

    
SCRIPT = """
chmod +w /usr/share/gdm/defaults.conf
sed -i 's/^GraphicalTheme=[a-zA-Z]*$/GraphicalTheme=%s/g' /usr/share/gdm/defaults.conf
chmod -w /usr/share/gdm/defaults.conf
"""
    
