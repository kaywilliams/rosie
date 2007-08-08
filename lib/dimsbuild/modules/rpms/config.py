from os.path import join

from dims import osutils

from dimsbuild.difftest import expand
from dimsbuild.event    import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib import RpmBuildHook, RpmsInterface

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
    
    self.configdir = osutils.dirname(interface.config.file)

    data = {
      'config': [
        '/distro/rpms/config-rpm',
      ],
      'input': [],
      'output': [],
    }

    installinfo = {
      'config' : ('/distro/rpms/config-rpm/config/script/path',
                  '/usr/lib/%s' % interface.product),
      'support': ('/distro/rpms/config-rpm/config/supporting-files/path',
                  '/usr/lib/%s' % interface.product),
    }

    packages = interface.config.xpath(
      '/distro/rpms/config-rpm/requires/package/text()', []
    )
    if packages:
      requires = ' '.join(packages)
    else:
      requires = None

    packages = interface.config.xpath(
      '/distro/rpms/config-rpm/obsoletes/package/text()', []
    )
    if packages:
      obsoletes = ' '.join(obsoletes)
    else:
      obsoletes = None

    RpmBuildHook.__init__(self, interface, data, 'config-rpm',
                           '%s-config' % interface.product,
                           summary='%s configuration script and '
                           'supporting files' % interface.fullname,
                           description='The %s-config provides scripts '
                           'and supporting files for configuring the '
                           '%s distribution' %(interface.product,
                                               interface.fullname),
                           installinfo=installinfo,
                           requires=requires,
                           obsoletes=obsoletes)
  
  def test_build(self):
    if RpmBuildHook.test_build(self):
      if self.interface.config.get('//config-rpm/requires', None) or \
         osutils.find(join(self.interface.SOURCES_DIR, self.id)) or \
         self.interface.config.get('//config-rpm/obsoletes', None) or \
         self.interface.config.get('//config-rpm/config/script/path/text()', None) or \
         self.interface.config.get('//config-rpm/config/supporting-files/path/text()', None):
        return True
    return False
  
  def _get_post_install(self):
    script = self.interface.config.get(self.installinfo['config'][0], None)
    if script:      
      post_install_scripts = find(location=self.output_location,
                                  name=osutils.basename(script),
                                  printf='%P')
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
    return None
