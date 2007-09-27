from dimsbuild.modules.rpms.lib import RpmBuildEvent

API_VERSION = 5.0

class DefaultThemeRpmEvent(RpmBuildEvent):
  def __init__(self):    
    self.themename = \
      self.config.get('/distro/rpms/default-theme-rpm/theme/text()', self.product)
    
    self.DATA = {
      'variables': ['product'],
      'config':    ['/distro/rpms/default-theme-rpm'],
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
                           defrequires='gdm',
                           id='default-theme-rpm')
    
  def validate(self):
    self.validator.validate('/distro/rpms/default-theme-rpm', 'default-theme-rpm.rng')

  def run(self):
    self.io.clean_eventcache(all=True)
    if self._test_build('False'):
      self._build_rpm()
    self.diff.write_metadata()    
  
  def apply(self):
    self.io.clean_eventcache()
    if not self._test_build('False'):
      return
    self._check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []      
    self.cvars['custom-rpms-info'].append((self.rpmname, 'conditional', 'gdm', self.obsoletes))
  
  def _getpscript(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(self.locals.default_theme % {'themename': self.themename})
    f.close()
    return 'postinstall.sh'

EVENTS = {'RPMS': [DefaultThemeRpmEvent]}
