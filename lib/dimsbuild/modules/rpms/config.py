from dims import pps

from dimsbuild.event import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib import RpmBuildHook, RpmsInterface

P = pps.Path

EVENTS = [
  {
    'id':        'config-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent':    'RPMS',
  }
]

API_VERSION = 4.0

HOOK_MAPPING = {
  'ConfigRpmHook': 'config-rpm',
  'ValidateHook' : 'validate',
}

class ValidateHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'rpms.config.validate'
    self.interface = interface

  def run(self):
    self.interface.validate('/distro/rpms/config-rpm',
                            schemafile='config-rpm.rng')
    
class ConfigRpmHook(RpmBuildHook):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'config.config-rpm'
    self.interface = interface

    self.DATA = {
      'config': [
        '/distro/rpms/config-rpm',
      ],
      'input': [],
      'output': [],
    }

    self.mdfile = self.interface.METADATA_DIR/'RPMS/config-rpm.md'

    RpmBuildHook.__init__(self, 'config-rpm')

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)

    kwargs = {}
    kwargs['release'] = self.interface.config.get('/distro/rpms/config-rpm/release/text()', '0')
    if self.interface.config.pathexists('/distro/rpms/config-rpm/requires/package/text()'):
      kwargs['requires'] = ' '.join(self.interface.config.xpath(
                           '/distro/rpms/config-rpm/requires/package/text()'))
    if self.interface.config.pathexists('/distro/rpms/config-rpm/obsoletes/package/text()'):    
      kwargs['obsoletes'] = ' '.join(self.interface.config.xpath(
                           '/distro/rpms/config-rpm/obsoletes/package/text()'))
    kwargs['provides'] = kwargs.get('obsoletes', None)
    installinfo = {
      'config' : ('/distro/rpms/config-rpm/config/script/path',
                  '/usr/lib/%s' % self.interface.product),
      'support': ('/distro/rpms/config-rpm/config/supporting-files/path',
                  '/usr/lib/%s' % self.interface.product),
    }
    
    self.register('%s-config' % self.interface.product,
                  'The %s-config provides scripts and supporting '\
                  'files for configuring the %s '\
                  'distribution.' %(self.interface.product, self.interface.fullname),
                  '%s configuration script and supporting files' % self.interface.fullname,
                  installinfo=installinfo,
                  **kwargs)
    self.add_data()
    
  def run(self):
    self.interface.remove_output(all=True)
    if not self.test_build('True'):
      return
    self.build_rpm()
    self.interface.write_metadata()    

  def apply(self):
    if not self.test_build('True'):
      return
    self.check_rpms()
    if not self.interface.cvars['custom-rpms-info']:
      self.interface.cvars['custom-rpms-info'] = []      
    self.interface.cvars['custom-rpms-info'].append((self.rpmname, 'mandatory', None, self.obsoletes))
  
  def test_build(self, default):
    if RpmBuildHook.test_build(self, default):
      if self.interface.config.get('//config-rpm/requires', None) or \
         self.interface.config.get('//config-rpm/obsoletes', None) or \
         self.interface.config.get('//config-rpm/config/script/path/text()', None) or \
         self.interface.config.get('//config-rpm/config/supporting-files/path/text()', None) or \
         (self.interface.SOURCES_DIR/self.name).findpaths():
        return True
    return False
  
  def getpscript(self):
    script = self.interface.config.get(self.installinfo['config'][0], None)
    if script:
      post_install_scripts = self.output_location.findpaths(glob=P(script).basename)
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
    return None
