from os.path import join

from dims.osutils import basename, dirname, find

from difftest import expand
from event    import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from main     import tree

from rpms.lib import RpmsHandler, RpmsInterface

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
}

class ConfigRpmHook(RpmsHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'config.config-rpm'
    self.eventid = 'config-rpm'

    self.configdir = dirname(interface.config.file)

    input = []
    for x in interface.config.xpath('//rpms/config-rpm/config/script/path/text()', []) + \
        interface.config.xpath('//rpms/config-rpm/config/supporting-files/path/text()', []):
      input.append(join(self.configdir, x))

    data = {
      'config': [
        '//rpms/config-rpm',
      ],
      'input': input,
      'output': [
        join(interface.METADATA_DIR, 'config-rpm'),
      ],
    }

    RpmsHandler.__init__(self, interface, data,
                         elementname='config-rpm',
                         rpmname='%s-config' %(interface.product,),
                         description='%s configuration script and supporting files' \
                         %(interface.fullname,),
                         long_description='The %s-config provides scripts and supporting files for'\
                         'configuring the %s distribution' %(interface.product, interface.fullname,))
    
  def test_build_rpm(self):
    return (self.config.get('//rpms/config-rpm/requires', None) or \
            self.config.get('//rpms/config-rpm/obsoletes', None) or \
            self.config.get('//rpms/config-rpm/config/script/path/text()', None) or \
            self.config.get('//rpms/config-rpm/config/supporting-files/path/text()', None) \
            is not None) and \
            (not self.interface.isSkipped(self.eventid) or self.interface.isForced(self.eventid))
             
    
  def get_post_install(self):
    script = self.config.get('//rpms/config-rpm/config/script/path/text()', None)
    if script:      
      post_install_scripts = find(location=self.output_location,
                                  name=basename(script),
                                  prefix=False)
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
    return None

  def get_requires(self):
    packages = self.config.xpath('//rpms/config-rpm/requires/package/text()', [])
    if packages:
      return ' '.join(packages)
    return None

  def get_obsoletes(self):
    packages = self.config.xpath('//rpms/config-rpm/obsoletes/package/text()', [])
    if packages:
      return ' '.join(packages)
    return None    

  def create_manifest(self): pass # done by get_data_files(), below.
  
  def get_data_files(self):
    lib_files = tree(self.output_location, type='f|l', prefix=False)
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    for file in lib_files:
      f.write('%s\n' %(file,))
    f.close()
    return ''.join(['/usr/lib/%s/ : ' %(self.product,), ', '.join(lib_files)])
