from ConfigParser import ConfigParser
from dims.osutils import basename, find
from dims.sync    import sync
from event        import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from lib          import RpmHandler, RpmsInterface
from os.path      import exists, join
from output       import tree

EVENTS = [
  {
    'id': 'config-rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['config-rpm'],
    'parent': 'RPMS',
  }
]

API_VERSION = 4.0

HOOK_MAPPING = {
  'ConfigRpmHook': 'config-rpm',
}

class ConfigRpmHook(RpmHandler):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'config.config-rpm'
    self.eventid = 'config-rpm'
    
    data = {
      'config': ['//rpms/config-rpm'],
      'input':  [interface.config.mget('//rpms/config-rpm/config/script/path/text()', []),
                 interface.config.mget('//rpms/config-rpm/config/supporting-files/path/text()', [])],
      'output': [join(interface.METADATA_DIR, 'config-rpm')]
    }
    
    requires = ' '.join(interface.config.mget('//rpms/config-rpm/requires/package/text()', []))
    obsoletes = ' '.join(interface.config.mget('//rpms/config-rpm/obsoletes/package/text()', []))
    RpmHandler.__init__(self, interface, data,
                        elementname='config-rpm',
                        rpmname='%s-config' %(interface.product,),
                        requires=requires,
                        obsoletes=obsoletes,
                        description='%s configuration script and supporting files' %(interface.fullname,),
                        long_description='The %s-config provides scripts and supporting files for'\
                        'configuring the %s distribution' %(interface.product, interface.fullname,))

    self.create = self.interface.isForced(self.eventid) or \
                  (self.config.get('//rpms/config-rpm/requires', None) or \
                   self.config.get('//rpms/config-rpm/obsoletes', None) or \
                   self.config.get('//rpms/config-rpm/config/script/path/text()', None) or \
                   self.config.get('//rpms/config-rpm/config/supporting-files/path/text()', None) \
                   is not None)

    # all the relative paths in the config file's <config-rpm> section
    # are relative to the config file's directory.
    self.expand_input()
      
  def get_post_install_script(self):
    script = self.config.get('//rpms/config-rpm/config/script/path/text()', None)
    if script:      
      post_install_scripts = find(location=self.output_location,
                                 name=basename(script),
                                 prefix=False)
      assert len(post_install_scripts) == 1
      return post_install_scripts[0]
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
