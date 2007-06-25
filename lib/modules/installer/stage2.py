from os.path import join

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from installer.lib import FileDownloadMixin

API_VERSION = 4.1

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'stage2-images',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['stage2'],
    'requires': ['anaconda-version', 'source-vars'],
    'parent': 'INSTALLER',
  },
]

HOOK_MAPPING = {
  'Stage2Hook': 'stage2-images',
}


#------ HOOKS ------#
class Stage2Hook(FileDownloadMixin):
  def __init__(self, interface):
    self.VERSION = 0
    self.ID = 'installer.stage2.stage2-images'
    
    self.interface = interface
    
    FileDownloadMixin.__init__(self, interface, self.interface.getBaseStore())
  
  def run(self):
    self.interface.log(0, "synchronizing stage2 images")
    
    self.register_file_locals(L_FILES)
    
    # download files, see FileDownloadMixin.download() in lib.py
    self.download()


#------ LOCALS ------#
L_FILES = ''' 
<locals>
  <files-entries>
    <files version="0">
      <file id="stage2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="netstg2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
      <file id="hdstg2.img">
        <path>
          <string-format string="%s/base">
            <format>
              <item>product</item>
            </format>
          </string-format>
        </path>
      </file>
    </files>

    <!-- 10.89.1.1 - netstg2.img and hdstg2.img combined into minstg2.img -->
    <files version="10.89.1.1">
      <action type="delete" path="file[@id='netstg2.img']"/>
      <action type="delete" path="file[@id='hdstg2.img']"/>
      <action type="insert" path=".">
        <file id="minstg2.img">
          <path>
            <string-format string="%s/base">
              <format>
                <item>product</item>
              </format>
            </string-format>
          </path>
        </file>
      </action>
    </files>

    <!-- 11.1.0.51-1 - images moved from $PROD/base/ to images/ -->
    <files version="11.1.0.51-1">
      <action type="update" path="file[@id='stage2.img']">
        <path>images</path>
      </action>
      <action type="update" path="file[@id='minstg2.img']">
        <path>images</path>
      </action>
    </files>

  </files-entries>
</locals>
'''
