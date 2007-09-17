from dimsbuild.modules.rpms.lib    import RpmBuildEvent
from dimsbuild.modules.rpms.locals import SCRIPT

API_VERSION = 5.0

class DefaultThemeRpmEvent(RpmBuildEvent):
  def __init__(self):
    RpmBuildEvent.__init__(self,
      id = 'default-theme-rpm',
    )
    
    self.DATA = {
      'config': [
        '/distro/rpms/default-theme-rpm',
      ],
      'output': [],
    }
    
    self.themename = \
      self.config.get('/distro/rpms/default-theme-rpm/theme/text()', self.product)
    
  def _validate(self):
    self.validate('/distro/rpms/default-theme-rpm', 'default-theme-rpm.rng')
  
  def _setup(self):
    self.setup_diff(self.DATA)
    
    kwargs = {}
    kwargs['requires'] = 'gdm'
    kwargs['release']  = self.config.get('/distro/rpms/default-theme-rpm/release/text()',
                                                   '0')
    self.register('%s-default-theme' % self.product,
                  'The %s-default-theme package requires the gdm package. '\
                  'Its sole function is to modify the value of the GraphicalTheme '\
                  'attribute in /usr/share/gdm/defaults.conf to the %s '
                  'theme.' %(self.product, self.themename),
                  'Script to set default gdm graphical theme',
                  **kwargs)
    self.add_data()
  
  def _run(self):
    self.remove_output(all=True)
    if not self.test_build('False'):
      return
    self.build_rpm()
    self.write_metadata()    
  
  def _apply(self):
    if not self.test_build('False'):
      return
    self.check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []      
    self.cvars['custom-rpms-info'].append((self.rpmname, 'conditional', 'gdm', self.obsoletes))
  
  def getpscript(self):
    f = (self.build_folder/'postinstall.sh').open('w')
    f.write(SCRIPT % self.themename)
    f.close()
    return 'postinstall.sh'

EVENTS = {'RPMS': [DefaultThemeRpmEvent]}
