from dimsbuild.modules.rpms.lib    import RpmBuildEvent
from dimsbuild.modules.rpms.locals import SCRIPT

API_VERSION = 5.0

class DefaultThemeRpmEvent(RpmBuildEvent):
  def __init__(self):    
    self.themename = \
      self.config.get('/distro/default-theme-rpm/theme/text()', self.product)
    
    data = {
      'variables': ['product'],
      'config':    ['/distro/default-theme-rpm'],
      'input' :    [],
      'output':    [],
    }
    
    RpmBuildEvent.__init__(self,
                           '%s-default-theme' % self.product,
                           'The %s-default-theme package requires the gdm package. '\
                           'Its sole function is to modify the value of the GraphicalTheme '\
                           'attribute in /usr/share/gdm/defaults.conf to the %s '
                           'theme.' %(self.product, self.themename),
                           'Script to set default gdm graphical theme',
                           data,
                           defrequires='gdm',
                           id='default-theme-rpm')
    
  def validate(self):
    self.validator.validate('/distro/default-theme-rpm', 'default-theme-rpm.rng')

  def run(self):
    self.remove_output(all=True)
    if not self._test_build('False'):
      return
    self._build_rpm()
    self._add_output()    
    self.write_metadata()    
  
  def apply(self):
    if not self._test_build('False'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []      
    self.cvars['custom-rpms-info'].append((self.rpmname, 'conditional', 'gdm', self.obsoletes))
  
  def _getpscript(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(SCRIPT % self.themename)
    f.close()
    return 'postinstall.sh'

EVENTS = {'RPMS': [DefaultThemeRpmEvent]}
