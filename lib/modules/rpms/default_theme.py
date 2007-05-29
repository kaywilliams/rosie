from event   import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from lib     import RpmHandler, RpmsInterface
from os.path import join

EVENTS = [{
  'id': 'default_theme_rpm',
  'interface': 'RpmsInterface',
  'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
  'provides': ['default-theme'],
  'parent': 'RPMS',
}]

def predefault_theme_rpm_hook(interface):
  handler = ThemeRpmHandler(interface)
  interface.add_handler('default_theme_rpm', handler)
  interface.disableEvent('default_theme_rpm')
  if handler.pre() or (interface.eventForceStatus('default_theme_rpm') or False):
    interface.enableEvent('default_theme_rpm')

def default_theme_rpm_hook(interface):
  interface.log(0, "creating the default theme rpm")
  handler = interface.get_handler('default_theme_rpm')
  handler.modify()

def postdefault_theme_rpm_hook(interface):
  handler = interface.get_handler('default_theme_rpm')
  if handler.create:
    interface.append_cvar('included-packages', [(handler.rpmname, 'conditional', 'gdm')])


class ThemeRpmHandler(RpmHandler):
  def __init__(self, interface):
    data = {
      'config': ['//rpms/default-theme-rpm'],
      'output': [join(interface.getMetadata(), 'default-theme-rpm/')],
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
    
