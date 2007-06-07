from dims.osutils import find
from event        import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from lib          import RpmHandler, RpmsInterface
from os.path      import join

EVENTS = [
  {
    'id': 'default-theme-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['default-theme-rpm'],
    'parent': 'RPMS', 
  },
]

HOOK_MAPPING = {
  'DefaultThemeHook': 'default-theme-rpm',
}

API_VERSION = 4.0

class DefaultThemeHook(RpmHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'default_them.default_theme_rpm'
    
    data = {
      'config': ['//rpms/default-theme-rpm'],
      'output': [join(interface.METADATA_DIR, 'default-theme-rpm/')],
    }
    self.themename = interface.config.get('//rpms/default-theme-rpm/theme/text()', interface.product)
    RpmHandler.__init__(self, interface, data,
                        elementname='default-theme-rpm',
                        rpmname='%s-default-theme' %(interface.product,),
                        requires='gdm',
                        description='Script to set default gdm graphical theme',
                        long_description='The %s-default-theme package requires the gdm package. '
                        ' Its sole function is to modify the value of the GraphicalTheme attribute in'
                        ' /usr/share/gdm/defaults.conf to the %s theme' %(interface.product,
                                                                          self.themename,))
  def apply(self):
    try:
      find(join(self.interface.METADATA_DIR, 'localrepo', 'RPMS'),
           name='%s*.[Rr][Pp][Mm]' %(self.rpmname,), prefix=False)[0]
    except IndexError:
      raise RuntimeError("missing rpm: '%s'" %(self.rpmname,))
    # add rpms to the included-packages control var, so that
    # they are added to the comps.xml
    self.interface.append_cvar('included-packages', [(self.rpmname, 'conditional', 'gdm')])
    
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
    
