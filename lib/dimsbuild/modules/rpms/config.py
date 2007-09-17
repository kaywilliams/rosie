from dims import pps

from dimsbuild.modules.rpms.lib import RpmBuildEvent

P = pps.Path

API_VERSION = 5.0


class ConfigRpmEvent(RpmBuildEvent):
  def __init__(self):
    RpmBuildEvent.__init__(self,
      id = 'config-rpm'
    )
    
    self.DATA = {
      'config': [
        '/distro/rpms/config-rpm',
      ],
      'input': [],
      'output': [],
    }
    
  def _validate(self):
    self.validate('/distro/rpms/config-rpm', 'config-rpm.rng')
  
  def _setup(self):
    self.setup_diff(self.DATA)
    
    kwargs = {}
    kwargs['release'] = self.config.get('/distro/rpms/config-rpm/release/text()', '0')
    if self.config.pathexists('/distro/rpms/config-rpm/requires/package/text()'):
      kwargs['requires'] = ' '.join(self.config.xpath(
                           '/distro/rpms/config-rpm/requires/package/text()'))
    if self.config.pathexists('/distro/rpms/config-rpm/obsoletes/package/text()'):    
      kwargs['obsoletes'] = ' '.join(self.config.xpath(
                           '/distro/rpms/config-rpm/obsoletes/package/text()'))
    kwargs['provides'] = kwargs.get('obsoletes', None)
    installinfo = {
      'config' : ('/distro/rpms/config-rpm/config/script/path',
                  '/usr/lib/%s' % self.product),
      'support': ('/distro/rpms/config-rpm/config/supporting-files/path',
                  '/usr/lib/%s' % self.product),
    }
    
    self.register('%s-config' % self.product,
                  'The %s-config provides scripts and supporting '\
                  'files for configuring the %s '\
                  'distribution.' %(self.product, self.fullname),
                  '%s configuration script and supporting files' % self.fullname,
                  installinfo=installinfo,
                  **kwargs)
    self.add_data()
    
  def _run(self):
    self.remove_output(all=True)
    if not self.test_build('True'):
      return
    self.build_rpm()
    self.write_metadata()    

  def _apply(self):
    if not self.test_build('True'):
      return
    self.check_rpms()
    if not self.cvars['custom-rpms-info']:
      self.cvars['custom-rpms-info'] = []      
    self.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))
  
  def test_build(self, default):
    if RpmBuildEvent.test_build(self, default):
      if self.config.get('//config-rpm/requires', None) or \
         self.config.get('//config-rpm/obsoletes', None) or \
         self.config.get('//config-rpm/config/script/path/text()', None) or \
         self.config.get('//config-rpm/config/supporting-files/path/text()', None) or \
         (self.SOURCES_DIR/self.id).findpaths():
        return True
    return False
  
  def getpscript(self):
    script = self.config.get(self.installinfo['config'][0], None)
    if script:
      post_install_scripts = self.output_location.findpaths(glob=P(script).basename)
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
    return None

EVENTS = {'RPMS': [ConfigRpmEvent]}
