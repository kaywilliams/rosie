from dimsbuild.event    import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

API_VERSION = 4.0

EVENTS = [
  {
    'id': 'pxeboot-images',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['pxeboot'],
    'requires': ['isolinux'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'PxebootHook': 'pxeboot-images',
}


#------ HOOKS ------#
class PxebootHook:
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.pxeboot.pxeboot-images'
    
    self.interface = interface

    self.DATA = {
      'input':  [],
      'output': [],      
    }
    self.mdfile = self.interface.METADATA_DIR/'INSTALLER/pxeboot.md'
    self.pxebootdir = self.interface.SOFTWARE_STORE/'images/pxeboot'

  def setup(self):
    self.interface.setup_diff(self.mdfile, self.DATA)
    paths = []
    for file in ['vmlinuz', 'initrd.img']:
      paths.append(self.interface.SOFTWARE_STORE/'isolinux'/file)
    self.interface.setup_sync(self.pxebootdir, paths=paths)
    
  def clean(self):
    self.interface.log(0, "cleaning pxeboot-images event")
    self.interface.remove_output(all=True)
    self.interface.clean_metadata()  

  def check(self):
    return self.interface.test_diffs()
  
  def run(self):
    self.interface.log(0, "preparing pxeboot images")
    self.interface.remove_output()
    self.interface.sync_input()
    self.interface.write_metadata()
  
  def apply(self):
    for file in ['vmlinuz', 'initrd.img']:
      if not (self.pxebootdir/file).exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file, self.pxebootdir))
