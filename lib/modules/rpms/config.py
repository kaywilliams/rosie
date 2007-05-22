from ConfigParser import ConfigParser
from dims.osutils import basename, find
from dims.sync    import sync
from event        import EVENT_TYPE_MDLR, EVENT_TYPE_PROC
from lib          import RpmHandler, RpmsInterface
from os.path      import exists, join
from output       import tree

EVENTS = [
  {
    'id': 'config_rpm',
    'interface': 'RpmsInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['config-rpm'],
    'parent': 'RPMS',
  }
]


def preconfig_rpm_hook(interface):
  handler = ConfigRpmHandler(interface)
  interface.add_handler('config-rpm', handler)
  interface.disableEvent('config_rpm')
  if (interface.eventForceStatus('config_rpm') or False) or handler.pre():
    interface.enableEvent('config_rpm')

def config_rpm_hook(interface):
  interface.log(0, "creating config rpm")
  handler = interface.get_handler('config-rpm')
  handler.modify()

def postconfig_rpm_hook(interface):
  handler = interface.get_handler('config-rpm')
  if handler.create:
    interface.append_cvar('included-packages', [handler.rpmname])


class ConfigRpmHandler(RpmHandler):
  def __init__(self, interface):
    data = {
      'config': ['//rpms/config-rpm'],
      'input':  [interface.config.mget('//rpms/config-rpm/config/script/path/text()', []),
                 interface.config.mget('//rpms/config-rpm/config/supporting-files/path/text()', [])],
      'output': [join(interface.getMetadata(), 'config-rpm')]
    }
    requires = ''.join(interface.config.mget('//rpms/config-rpm/requires/package/text()', []))
    obsoletes = ''.join(interface.config.mget('//rpms/config-rpm/obsoletes/package/text()', []))
    RpmHandler.__init__(self, interface, data,
                        elementname='config-rpm',
                        rpmname='%s-config' %(interface.product,),
                        requires=requires,
                        obsoletes=obsoletes,
                        description='%s configuration script and supporting files' %(interface.fullname,),
                        long_description='The %s-config provides scripts and supporting files for'\
                        'configuring the %s distribution' %(interface.product, interface.fullname,))

    # @override RpmHandler.create    
    self.create = (self.config.get('//rpms/config-rpm/requires', None) or \
                   self.config.get('//rpms/config-rpm/obsoletes', None)) is not None

  def setup(self):
    # overriding RpmHandler.setup() because need to add the post script
    RpmHandler.setup(self)
    script = self.config.get('//rpms/config-rpm/config/script/path/text()', None)
    if script:
      post_install_scripts = find(location=self.output_location,
                                 name=basename(script),
                                 prefix=False)
      assert len(post_install_scripts) == 1
      setup_cfg = join(self.output_location, 'setup.cfg')
      parser = ConfigParser()
      parser.read(setup_cfg)
      parser.set('bdist_rpm', 'post_install', post_install_scripts[0])
      f = open(setup_cfg, 'w')
      parser.write(f)
      f.close()
    
  def _get_data_files(self):
    lib_files = tree(self.output_location, type='f|l', prefix=False)
    manifest = join(self.output_location, 'MANIFEST')
    f = open(manifest, 'w')
    f.write('setup.py\n')
    f.write('setup.cfg\n')
    for file in lib_files:
      f.write('%s\n' %(file,))
    f.close()
    return ''.join(['/usr/lib/%s/ : ' %(self.product,), ', '.join(lib_files)])

