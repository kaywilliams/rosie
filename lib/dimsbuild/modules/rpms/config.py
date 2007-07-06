from os.path import join

from dims.osutils import basename, dirname, find

from dimsbuild.difftest import expand
from dimsbuild.event    import EVENT_TYPE_MDLR, EVENT_TYPE_PROC

from lib import RpmsHandler, RpmsInterface

EVENTS = [
  {
    'id': 'config-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'parent': 'RPMS',
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
    self.interface.validate('/distro/rpms/config-rpm', schemafile='config-rpm.rng')
    
class ConfigRpmHook(RpmsHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'config.config-rpm'
    
    self.configdir = dirname(interface.config.file)

    data = {
      'config': [
        '/distro/rpms/config-rpm',
      ],
      'input': [
        interface.config.xpath('/distro/rpms/config-rpm/config/script/path/text()', []),
        interface.config.xpath('/distro/rpms/config-rpm/config/supporting-files/path/text()', []),
      ],
      'output': [],
    }

    RpmsHandler.__init__(self, interface, data, 'config-rpm', '%s-config' %(interface.product,),
                         description='%s configuration script and supporting files' \
                         %(interface.fullname,),
                         long_description='The %s-config provides scripts and supporting files for'\
                         'configuring the %s distribution' %(interface.product, interface.fullname,))
  def setup(self):
    self.expandInput()
  
  def _test_build(self):
    return (self.config.get('/distro/rpms/config-rpm/requires', None) or \
            self.config.get('/distro/rpms/config-rpm/obsoletes', None) or \
            self.config.get('/distro/rpms/config-rpm/config/script/path/text()', None) or \
            self.config.get('/distro/rpms/config-rpm/config/supporting-files/path/text()', None) \
            is not None)
    
  def _get_post_install(self):
    script = self.config.get('/distro/rpms/config-rpm/config/script/path/text()', None)
    if script:      
      post_install_scripts = find(location=self.output_location,
                                  name=basename(script),
                                  prefix=False)
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
    return None

  def _get_requires(self):
    packages = self.config.xpath('/distro/rpms/config-rpm/requires/package/text()', [])
    if packages:
      return ' '.join(packages)
    return None

  def _get_obsoletes(self):
    packages = self.config.xpath('/distro/rpms/config-rpm/obsoletes/package/text()', [])
    if packages:
      return ' '.join(packages)
    return None    

  def _create_manifest(self): pass # done by get_data_files(), below.
  
  def _get_data_files(self):
    lib_files = find(self.output_location, name='*', type=0101)
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    for file in lib_files:
      f.write('%s\n' %(file,))
    f.close()
    return ''.join(['/usr/lib/%s/ : ' %(self.product,), ', '.join(lib_files)])
