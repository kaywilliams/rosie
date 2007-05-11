from os.path import join

from event import EVENT_TYPE_PROC, EVENT_TYPE_MDLR

from lib import FileDownloader, InstallerInterface

API_VERSION = 3.0

#------ EVENTS ------#
EVENTS = [
  {
    'id': 'stage2',
    'interface': 'InstallerInterface',
    'properties': EVENT_TYPE_PROC|EVENT_TYPE_MDLR,
    'provides': ['stage2'],
    'parent': 'INSTALLER',
  },
]


#------ HOOK FUNCTIONS ------#
def stage2_hook(interface):
  interface.log(0, "synchronizing stage2 images")
  i,_,_,d,_,_ = interface.getStoreInfo(interface.getBaseStore())
  
  dl = FileDownloader(L_FILES, interface)
  dl.download(d,i)


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
