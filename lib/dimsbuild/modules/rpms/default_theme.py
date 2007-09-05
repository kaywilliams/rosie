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
    self.interface = interface

    self.DATA = {
      'config': [
        '/distro/rpms/default-theme-rpm',
      ],
      'output': [],
    }
    self.mdfile = self.interface.METADATA_DIR/'RPMS/default-theme-rpm.md'

    self.themename = interface.config.get(
      '/distro/rpms/default-theme-rpm/theme/text()',
      interface.product
    )

    RpmBuildHook.__init__(self, 'default-theme-rpm')
    
  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    kwargs = {}
    kwargs['requires'] = 'gdm'
    kwargs['release']  = self.interface.config.get('/distro/rpms/default-theme-rpm/release/text()',
                                                   '0')
    self.register('%s-default-theme' % self.interface.product,
                  'The %s-default-theme package requires the gdm package. '\
                  'Its sole function is to modify the value of the GraphicalTheme '\
                  'attribute in /usr/share/gdm/defaults.conf to the %s '
                  'theme.' %(self.interface.product, self.themename),
                  'Script to set default gdm graphical theme',
                  **kwargs)
    self.add_data()

  def run(self):
    self.interface.remove_output(all=True)
    if not self.test_build('False'):
      return
    self.build_rpm()
    self.interface.write_metadata()    

  def apply(self):
    if not self.test_build('False'):
      return
    self.check_rpms()
    if not self.interface.cvars['custom-rpms-info']:
      self.interface.cvars['custom-rpms-info'] = []      
    self.interface.cvars['custom-rpms-info'].append((self.rpmname, 'conditional', 'gdm', self.obsoletes))

  def getpscript(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(SCRIPT % self.themename)
    f.close()
    return 'postinstall.sh'
