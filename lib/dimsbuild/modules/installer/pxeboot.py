from dimsbuild.event import Event

API_VERSION = 5.0


class PxebootImagesEvent(Event):
  def __init__(self):
    Event.__init__(self,
      id = 'pxeboot-images',
      provides = ['pxeboot'],
      requires = ['isolinux'],
    )

    self.DATA = {
      'input':  [],
      'output': [],      
    }
    
    self.mdfile = self.get_mdfile()
    self.pxebootdir = self.SOFTWARE_STORE/'images/pxeboot'
  
  def _setup(self):
    self.setup_diff(self.mdfile, self.DATA)
    paths = []
    for file in ['vmlinuz', 'initrd.img']:
      paths.append(self.SOFTWARE_STORE/'isolinux'/file)
    self.setup_sync(self.pxebootdir, paths=paths)
    
  def _clean(self):
    self.remove_output(all=True)
    self.clean_metadata()  

  def _check(self):
    return self.test_diffs()
  
  def _run(self):
    self.log(0, "preparing pxeboot images")
    self.remove_output()
    self.sync_input()
    self.write_metadata()
  
  def _apply(self):
    for file in ['vmlinuz', 'initrd.img']:
      if not (self.pxebootdir/file).exists():
        raise RuntimeError("Unable to find '%s' in '%s'" % (file, self.pxebootdir))


EVENTS = {'INSTALLER': [PxebootImagesEvent]}
