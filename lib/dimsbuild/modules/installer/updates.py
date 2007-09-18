from dimsbuild.event import Event

from dimsbuild.modules.installer.lib import ImageModifyMixin

API_VERSION = 5.0

class UpdatesImageEvent(Event, ImageModifyMixin):
  def __init__(self):
    Event.__init__(self,
      id = 'updates-image',
      provides = ['updates.img'],
      requires = ['buildstamp-file', 'anaconda-version'],
      conditionally_requires = ['logos'],
    )
    
    self.DATA = {
      'config':    ['/distro/installer/updates.img/path/text()'],
      'variables': ['cvars[\'anaconda-version\']'],
      'input':     [],
      'output':    [],
    }
    
    ImageModifyMixin.__init__(self, 'updates.img')
  
  def validate(self):
    self._validate('/distro/installer/updates.img', 'updates.rng')
  
  def error(self, e):
    try:
      self._close()
    except:
      pass
  
  def setup(self):
    ImageModifyMixin.setup(self)
    self._register_image_locals(L_IMAGES)
  
  def run(self):
    self.log(0, "generating updates.img")
    self.remove_output()
    self._modify()
    
  def apply(self):
    for file in self.list_output():
      if not file.exists():
        raise RuntimeError("Unable to find '%s' at '%s'" % (file.basename, file.dirname))


EVENTS = {'INSTALLER': [UpdatesImageEvent]}

#------ LOCALS ------#
L_IMAGES = ''' 
<locals>
  <images-entries>
    <images version="0">
      <image id="updates.img" virtual="True">
        <format>ext2</format>
        <path>images</path>
      </image>
    </images>
    
    <!-- 11.1.0.11-1 updates.img format changed to cpio, zipped -->
    <images version="11.1.0.11-1">
      <action type="update" path="image[@id='updates.img']">
        <format>cpio</format>
        <zipped>True</zipped>
      </action>
    </images>
  </images-entries>
</locals>
'''
